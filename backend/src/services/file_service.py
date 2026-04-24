import mimetypes
from typing import List
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, func, exists
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import File
from src.database import STORAGE_DIR 
from src.services.vector_db_service import vector_db_service
import os
import hashlib
import asyncio



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

    async def get_files_by_ids(self, session: AsyncSession, file_ids: List[str]) -> List[File]:
        unique_ids = list(set(str(f_id) for f_id in file_ids if f_id))
        
        if not unique_ids:
            return []


        query = select(File).where(File.id.in_(unique_ids))
        result = await session.execute(query)
        files = result.scalars().all()


        if not files and unique_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Ни один из указанных файлов не найден"
            )
            
        return list(files)

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
        try:
            vector_db_service.delete_document_by_id(file_id)
        except Exception as e:
            print(f"Ошибка при очистке Chroma: {e}")

    async def delete_files(self, session: AsyncSession):
        stmt = select(File)
        result = await session.execute(stmt)
        files_to_delete = result.scalars().all()
        
        count = 0
        for file_item in files_to_delete:
            stored_path = self.storage_dir / file_item.stored_name
            try:
                if os.path.exists(stored_path):
                    os.remove(stored_path)
            except Exception as e:
                print(f"Не удалось удалить файл {stored_path}: {e}")

            await session.delete(file_item)
            count += 1
        await session.commit()
        try:
            vector_db_service.clear_all_data()
        except Exception as e:
            print(f"Ошибка при очистке Chroma: {e}")
        return {
            "removed_files_count": count
        }


    async def create_hash(self, session: AsyncSession, file_id: str) -> None:
        file_item = await self.get_file(session, file_id)
        chunk_size = 102400
        stored_path = self.storage_dir / file_item.stored_name
        def compute_sync():
            if not os.path.exists(stored_path):
                return None
                
            with open(stored_path, "rb") as f:
                start_chunk = f.read(chunk_size)
                
                f.seek(0, os.SEEK_END)
                f_size = f.tell()
                
                if f_size > chunk_size * 2:
                    f.seek(-chunk_size, os.SEEK_END)
                    end_chunk = f.read(chunk_size)
                else:
                    end_chunk = f.read()
                    
                combined = start_chunk + end_chunk + str(f_size).encode()
                return hashlib.sha256(combined).hexdigest()

        loop = asyncio.get_running_loop()
        file_hash = await loop.run_in_executor(None, compute_sync)

        if file_hash:
            file_item.file_hash = file_hash
            await session.commit()

        await session.refresh(file_item)
        return file_item            

    async def is_duplicate(self, session: AsyncSession, file_id: str)-> bool:
        file_item = await self.get_file(session, file_id)
        file_item = await self.create_hash(session=session, file_id=file_id)

        duplicate_query = select(exists().where(
            File.file_hash == file_item.file_hash,
            File.size == file_item.size,
            File.id != file_id,
            File.status != "error"
        ))
        is_duplicate = (await session.execute(duplicate_query)).scalar()

        return is_duplicate

file_service = FileService(storage_dir=STORAGE_DIR)