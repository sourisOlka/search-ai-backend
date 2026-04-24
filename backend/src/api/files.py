from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from celery import chain
from starlette import status


from src.schemas.files import FileItem, FileUpdate, FilesPagination, RemovedFiles
from src.database import get_db, STORAGE_DIR
from src.services.file_service import file_service
from src.tasks.files import (
    check_file_extension, check_is_file_unique, 
    extract_file_metadata, create_file_embiddings, cleanup_after_failure
)


router = APIRouter(prefix="/files", tags=["Files"])

@router.get("", response_model=FilesPagination)
async def list_files_view(page: int = 1, size: int = 10, session: AsyncSession = Depends(get_db)):
    return await file_service.list_files(session=session, page=page, size=size)

@router.post("", response_model=FileItem, status_code=201)
async def create_file_view(
    title: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db)
):
    file_item = await file_service.create_file(session=session, title=title, upload_file=file)
    
    chain(
        check_file_extension.si(file_item.id),
        check_is_file_unique.si(file_item.id),
        extract_file_metadata.si(file_item.id),
        create_file_embiddings.si(file_item.id)
    ).apply_async(link_error=cleanup_after_failure.s(file_item.id))

    return file_item


@router.get("/{file_id}", response_model=FileItem)
async def get_file_view(file_id: str, session: AsyncSession = Depends(get_db)):
    return await file_service.get_file(session=session, file_id=file_id)


@router.patch("/{file_id}", response_model=FileItem)
async def update_file_view(
    file_id: str,
    payload: FileUpdate,
    session: AsyncSession = Depends(get_db)
):
    return await file_service.update_file(session=session, file_id=file_id, title=payload.title)


@router.get("/{file_id}/download")
async def download_file(file_id: str, session: AsyncSession = Depends(get_db)):
    file_item = await file_service.get_file(session=session, file_id = file_id)
    stored_path = STORAGE_DIR / file_item.stored_name
    if not stored_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")
    return FileResponse(
        path=stored_path,
        media_type=file_item.mime_type,
        filename=file_item.original_name,
    )


@router.delete("/{file_id}", status_code=204)
async def delete_file_view(file_id: str, session: AsyncSession = Depends(get_db)):
    await file_service.delete_file(session=session, file_id=file_id)

@router.delete("", response_model=RemovedFiles)
async def delete_files(session: AsyncSession = Depends(get_db)):
    return await file_service.delete_files(session=session)
