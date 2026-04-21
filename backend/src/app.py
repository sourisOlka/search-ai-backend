from fastapi import FastAPI, HTTPException, Depends
from fastapi import File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx, os
from celery import chain


from src.schemas.files import FileItem, FileUpdate, FilesPagination
from src.schemas.question import QuestionRequest
from src.database import get_db, STORAGE_DIR

from src.tasks.files import check_file_extension, extract_file_metadata, create_file_embiddings, cleanup_after_failure
from src.services.files import file_service
from src.services.ai_service import ai_service

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/files", response_model=FilesPagination)
async def list_files_view(page: int = 1, size: int = 10, session: AsyncSession = Depends(get_db)):
    return await file_service.list_files(session=session, page=page, size=size)

@app.post("/files", response_model=FileItem, status_code=201)
async def create_file_view(
    title: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db)
):
    file_item = await file_service.create_file(session=session, title=title, upload_file=file)
    
    chain(
        check_file_extension.si(file_item.id), 
        extract_file_metadata.si(file_item.id),
        create_file_embiddings.si(file_item.id)
    ).apply_async(link_error=cleanup_after_failure.s(file_item.id))

    return file_item


@app.get("/files/{file_id}", response_model=FileItem)
async def get_file_view(file_id: str, session: AsyncSession = Depends(get_db)):
    return await file_service.get_file(session=session, file_id=file_id)


@app.patch("/files/{file_id}", response_model=FileItem)
async def update_file_view(
    file_id: str,
    payload: FileUpdate,
    session: AsyncSession = Depends(get_db)
):
    return await file_service.update_file(session=session, file_id=file_id, title=payload.title)


@app.get("/files/{file_id}/download")
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


@app.delete("/files/{file_id}", status_code=204)
async def delete_file_view(file_id: str, session: AsyncSession = Depends(get_db)):
    await file_service.delete_file(session=session, file_id=file_id)


@app.post("/search", status_code=200)
async def analyze_question(request: QuestionRequest):
    ai_answer = await ai_service.analize(
        agent_id="classifier", 
        user_query=request.question
    )

    return {
        "status": "success",
        "question": request.question,
        "payload": ai_answer
    }