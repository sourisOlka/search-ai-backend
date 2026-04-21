from pathlib import Path
from src.worker import celery_app, run_async
from src.models import File
from src.database import STORAGE_DIR, async_session_maker
from src.services.pdf_service import PdfService

@celery_app.task(name="src.tasks.files.check_file_extension")
def check_file_extension(file_id: str):
    return run_async(_check_extension(file_id))

@celery_app.task(name="src.tasks.files.extract_file_metadata")
def extract_file_metadata(file_id: str):
    return run_async(_extract_metadata(file_id))

@celery_app.task(name="src.tasks.files.create_file_embiddings")
def create_file_embiddings(file_id: str):
    return run_async(_create_embiddings(file_id))

@celery_app.task(name="src.tasks.files.cleanup_after_failure")
def cleanup_after_failure(request, exc, traceback, file_id):
    print(f"Очистка файла {file_id} после ошибки: {exc}")
    run_async(_delete_file_from_disk(file_id))

async def _check_extension(file_id: str):
    async with async_session_maker() as session:
        file_item = await session.get(File, file_id)
        if not file_item:
            raise ValueError(f"File not found. Processing stopped.") 

        file_item.status = "processing"
        extension = Path(file_item.original_name).suffix.lower()

        if extension != ".pdf":
            file_item.status = "failed"
            await session.commit()
            raise ValueError(f"Invalid extension {extension}. Processing stopped.") 

        await session.commit()


async def _extract_metadata(file_id: str):
    async with async_session_maker() as session:
        file_item = await session.get(File, file_id)
        if not file_item or file_item.status == "failed":
            raise ValueError(f"File {file_id} invalid or missing.")

        stored_path = STORAGE_DIR / file_item.stored_name
        if not stored_path.exists():
            file_item.status = "failed"
            await session.commit()
            raise FileNotFoundError(f"Physical file {file_item.stored_name} not found.")

        metadata = {
            "extension": Path(file_item.original_name).suffix.lower(),
            "size_bytes": file_item.size,
        }

        try:
            content = stored_path.read_bytes()
            metadata["approx_page_count"] = max(content.count(b"/Type /Page"), 1)
            file_item.metadata_json = metadata
            file_item.status = "processed"
            
        except Exception as e:
            file_item.status = "failed"
            await session.commit()
            raise ValueError(f"Metadata extraction failed: {str(e)}") 
    await session.commit()

async def _delete_file_from_disk(file_id: str):
    async with async_session_maker() as session:
        file_item = await session.get(File, file_id)
        if file_item:
            stored_path = STORAGE_DIR / file_item.stored_name
            if stored_path.exists():
                stored_path.unlink()

async def _create_embiddings(file_id: str):
    async with async_session_maker() as session:
        file_item = await session.get(File, file_id)
        if not file_item or file_item.status == "failed":
            raise ValueError(f"File {file_id} invalid or missing.")
        file_item.status = "processing"
        await session.commit()
        try:
            service = PdfService(file_id=file_id)
            await service.run(session)
            
        except Exception as e:
            file_item.status = "error"
            await session.commit()
            raise e
        
