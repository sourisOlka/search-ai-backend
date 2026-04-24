from pathlib import Path
from src.worker import celery_app, run_async
from src.models import File
from src.database import async_session_maker
from src.services.pdf_service import PdfService
from src.services.file_service import file_service
from src.services.ai_service import ai_service
from src.services.vector_db_service import vector_db_service
import re
import json

@celery_app.task(name="src.tasks.search.search_similar")
def search_similar(question: str):
    return run_async(_search_similar(question))



async def _search_similar(question: str):
    async with async_session_maker() as session:

        classification = await ai_service.analize(
            agent_id="classifier", 
            user_query=question
        )
        
        search_target = classification.get("search_target", question)
        action = classification.get("action", question)
        similar_chunks = await vector_db_service.search_similar(query=search_target, k=5)
        print(f"поиск окончен target={search_target} action={action}")
        
        

        user_query = (
                f"ИНСТРУКЦИЯ ПОЛЬЗОВАТЕЛЯ: {question}\n"
                f"ТРЕБУЕМЫЙ ФОРМАТ (action): {action}\n\n"
                f"КОНТЕКСТ ИЗ ДОКУМЕНТОВ:\n" + 
                "".join([chunk["content"] for chunk in similar_chunks])
            )

        raw_response = await ai_service.analize(
            agent_id="create_scheme", 
            user_query=user_query
        )
        print(f"\n{'='*20} ГЕНЕРАЦИЯ ОТВЕТА {raw_response}\n")

        
        context_parts = []

        print(f"\n{'='*20} НАЙДЕННЫЕ МАТЕРИАЛЫ {'='*20}")

        file_ids = [chunk["metadata"].get("file_id") for chunk in similar_chunks]
        files = await file_service.get_files_by_ids(session, file_ids)
        files_map = {str(f.id): f for f in files}

        for i, chunk in enumerate(similar_chunks, 1):
            content = chunk["content"]
            page = chunk["metadata"].get("page", "?")
            file_id = str(chunk["metadata"].get("file_id", "unknown"))
            score = chunk["score"]

            # 3. Достаем красивое имя файла из нашей мапы
            file_item = files_map.get(file_id)
            file_name = file_item.original_name if file_item else "Неизвестный файл"

            # Формируем человекочитаемый заголовок
            chunk_header = f"[Файл: {file_name}, Страница: {page}]"
            context_parts.append(f"{chunk_header}\n{content}")

            print(f" Чанк №{i} (Score: {score})")
            print(f" {chunk_header}") # Здесь теперь имя вместо UUID
            print(f" Текст: {content[:200]}...") 
            print(f"{'-'*60}")

  
        context_text = "\n\n".join(context_parts)

        if not context_text:
            context_text = "Релевантная информация в базе данных не найдена."
            print(" Поиск не дал результатов.")
            
        return {
            "classification": classification,
            "chunks": similar_chunks
        }
        