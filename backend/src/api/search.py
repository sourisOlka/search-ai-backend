from fastapi import APIRouter
from celery import chain

from src.schemas.question import QuestionRequest
from src.services.ai_service import ai_service
from src.tasks.search import search_similar


router = APIRouter(prefix="/search", tags=["Search"])

@router.post("", status_code=200)
async def analyze_question(request: QuestionRequest):
    chain(
        search_similar.s(request.question),
    ).apply_async()


    return {
        "status": "processed",
        "question": request.question,
    }