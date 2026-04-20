from pathlib import Path
from src.worker import celery_app, run_async
from src.models import File
from src.database import STORAGE_DIR, async_session_maker

@celery_app.task(name="src.tasks.files.check_file_extension")
def check_file_extension(file_id: str):
    return run_async(_check_extension(file_id))

@celery_app.task(name="src.tasks.files.extract_file_metadata")
def extract_file_metadata(file_id: str):
    return run_async(_extract_metadata(file_id))

async def _check_extension(file_id: str):
    async with async_session_maker() as session:
        file_item = await session.get(File, file_id)
        if not file_item:
            return

        file_item.status = "processing"
        extension = Path(file_item.original_name).suffix.lower()

        if extension != ".pdf":
            file_item.status = "failed"
            await session.commit()
            return 

        await session.commit()


async def _extract_metadata(file_id: str):
    async with async_session_maker() as session:
        file_item = await session.get(File, file_id)
        if not file_item or file_item.status == "failed":
            return

        stored_path = STORAGE_DIR / file_item.stored_name
        if not stored_path.exists():
            file_item.status = "failed"
            await session.commit()
            return

        metadata = {
            "extension": Path(file_item.original_name).suffix.lower(),
            "size_bytes": file_item.size,
        }

        try:
            content = stored_path.read_bytes()
            metadata["approx_page_count"] = max(content.count(b"/Type /Page"), 1)
            file_item.metadata_json = metadata
            file_item.status = "processed"
        except Exception:
            file_item.status = "failed"
            
        await session.commit()