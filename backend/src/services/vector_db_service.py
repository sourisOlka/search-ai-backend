from typing import List, Dict, Any
from langchain_chroma import Chroma
import asyncio
from src.services.ai_service import ai_service
from src.core.ai_config import CHROMA_DB_DIR
import hashlib
import gc


class VectorDBService:
    def __init__(self):
        self.vector_db = None
        self.embeddings = None

    def init_vector_db(self):
        if self.vector_db is not None:
            return self.vector_db
        
        print("Инициализация базы и модели... (один раз)")

        self.embeddings = ai_service.get_embeddings()
        self.vector_db = Chroma(
            collection_name="pdf_documents",
            embedding_function=self.embeddings,
            persist_directory=str(CHROMA_DB_DIR)
        )

    async def add_texts(
        self, 
        texts_to_embed: List[str], 
        metadatas: List[Dict[str, Any]]
    ) -> None: 
        self.init_vector_db()
        ids = [hashlib.md5(t.encode()).hexdigest() for t in texts_to_embed]
        
        await asyncio.to_thread(
            self.vector_db.add_texts,
            texts=texts_to_embed,
            metadatas=metadatas,
            ids=ids
        )

    async def search_similar(self, query: str | List[str], k: int = 5) -> List[Dict[str, Any]]:
        if isinstance(query, list):
            query = " ".join([str(i) for i in query]) 
        
        if not query or not str(query).strip():
            return []

        query_str = str(query).strip()
        self.vector_db = None
        self.init_vector_db()

        try:
            docs_with_scores = await asyncio.to_thread(
                self.vector_db.similarity_search_with_score, 
                query_str, 
                k=k
            )


            results = []
            for doc, score in docs_with_scores:
                if score > 1.1:
                    continue

                file_id = doc.metadata.get("file_id")
                page_num = doc.metadata.get("page")
               

                results.append({
                    "content": doc.page_content,
                    "score": round(float(score), 4),
                    "location": f"Файл: {file_id}, Стр: {page_num}", # Красивая ссылка для промпта
                    "metadata": {
                        "file_id": file_id,
                        "page": page_num
                    }
                })

            return sorted(results, key=lambda x: x["score"])

        except Exception as e:
            print(f"Ошибка поиска в Chroma: {e}")
            return []

    def get_all_documents(self):
        self.init_vector_db()
        data = self.vector_db._collection.get(include=["metadatas"])
        
        if not data or not data["metadatas"]:
            return []


        unique_file_ids = {m["file_id"] for m in data["metadatas"] if "file_id" in m}
        
        return list(unique_file_ids)
    
    def delete_document_by_id(self, file_id: str) -> None:
        self.init_vector_db()
        self.vector_db._collection.delete(where={"file_id": str(file_id)})
        print(f"DEBUG: Все чанки файла {file_id} удалены из базы")

    def clear_all_data(self) -> None:
        self.init_vector_db()
        all_data = self.vector_db._collection.get()
        ids = all_data.get("ids")
        
        if ids:
            self.vector_db._collection.delete(ids=ids)
            print(f"DEBUG: База полностью очищена. Удалено {len(ids)} записей.")
        else:
            print("DEBUG: База и так пуста.")

vector_db_service = VectorDBService()        