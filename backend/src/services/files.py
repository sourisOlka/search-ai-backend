import mimetypes
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import File
from src.database import STORAGE_DIR # Или брать из settings

class FileService:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def list_files(self, session: AsyncSession, page: int | None = None, size: int | None = None):
        count_query = select(func.count()).select_from(File)
        total_result = await session.execute(count_query)
        total_count = total_result.scalar() or 0

        query = select(File).order_by(File.created_at.desc())
        
        if page and size:
            query = query.offset((page - 1) * size).limit(size)
            
        result = await session.execute(query)
        return {
            "files": list(result.scalars().all()),
            "total_count": total_count
        }

    async def get_file(self, session: AsyncSession, file_id: str) -> File:
        file_item = await session.get(File, file_id)
        if not file_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return file_item

    async def create_file(self, session: AsyncSession, title: str, upload_file: UploadFile) -> File:
        content = await upload_file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")

        file_id = str(uuid4())
        suffix = Path(upload_file.filename or "").suffix
        stored_name = f"{file_id}{suffix}"
        stored_path = self.storage_dir / stored_name
        

        stored_path.write_bytes(content)

        file_item = File(
            id=file_id,
            title=title,
            original_name=upload_file.filename or stored_name,
            stored_name=stored_name,
            mime_type=upload_file.content_type or mimetypes.guess_type(stored_name)[0] or "application/octet-stream",
            size=len(content),
            status="uploaded",
        )
        session.add(file_item)
        await session.commit()
        await session.refresh(file_item)
        return file_item

    async def delete_file(self, session: AsyncSession, file_id: str) -> None:
        file_item = await self.get_file(session, file_id)
        stored_path = self.storage_dir / file_item.stored_name
        if stored_path.exists():
            stored_path.unlink()
        await session.delete(file_item)
        await session.commit()

file_service = FileService(storage_dir=STORAGE_DIR)