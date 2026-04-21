from sqlalchemy.ext.asyncio import AsyncSession
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
import fitz
from src.services.fix_words_service import fix_words_service
from src.services.ai_service import ai_service
from src.core.ai_config import CHROMA_DB_DIR
from src.database import STORAGE_DIR
from src.models import File



class PdfService:
    def __init__(
        self, 
        file_id: str, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200
    ):
        self.file_id = file_id
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def run(self, session: AsyncSession):
        file_item = await session.get(File, self.file_id)
        if not file_item:
            return
        
        stored_path = STORAGE_DIR / file_item.stored_name          
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

        try:
            doc = fitz.open(str(stored_path))
            texts_to_embed = []
            metadatas = []

            for page_num, page in enumerate(doc):
                blocks = page.get_text("dict")["blocks"]
                page_text_blocks = [] # Список строк для текущей страницы
                
                for b in blocks:
                    if "lines" not in b: continue
                    for l in b["lines"]:
                        if l["dir"] != (1.0, 0.0): continue
                        

                        line_text = "".join([s["text"] for s in l["spans"]])
                        fixed_line = fix_words_service.fix_broken_words(line_text)
                        
                        if not fixed_line.strip(): continue

                        if not page_text_blocks:
                            page_text_blocks.append(fixed_line)
                        else:
                            last_content = page_text_blocks[-1].rstrip()

                            if last_content.endswith("-"):
                                page_text_blocks[-1] = last_content[:-1] + fixed_line
                            else:
                                parts = last_content.rsplit(' ', 1)
                                
                                res = fix_words_service.smart_suffix_fix(parts[-1].strip() + " " + fixed_line)

                                if len(parts) > 1:
                                    page_text_blocks[-1] = parts[0].strip() + " " + res
                                else:
                                    page_text_blocks[-1] = res

                page_content = " ".join(page_text_blocks)
                page_chunks = text_splitter.split_text(page_content)


                for chunk_text in page_chunks:
                    texts_to_embed.append(chunk_text.strip())
                    metadatas.append({
                        "file_id": str(self.file_id),
                        "page": page_num + 1
                    })
            
            if texts_to_embed:
                embeddings = ai_service.get_embeddings()
                
                vector_db = Chroma(
                    collection_name="pdf_documents",
                    embedding_function=embeddings,
                    persist_directory=CHROMA_DB_DIR
                )
                
                vector_db.add_texts(texts=texts_to_embed, metadatas=metadatas)

            file_item.status = "completed"
            await session.commit()

        except Exception as e:
            await session.rollback()
            file_item.status = "error"
            await session.commit()
            raise e
        finally:
            if 'doc' in locals():
                doc.close()
      