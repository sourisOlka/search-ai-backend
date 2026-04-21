from src.schemas.ai_model import AiModelSettings
import os

CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR")
AI_AGENTS = {
    "classifier": AiModelSettings(
        model_name="llama3",
        api_type = "ollama",
        base_url = os.getenv("OLLAMA_URL"),
        temperature=0.0,
        system_prompt=(
            "Ты — аналитик. Разбери запрос пользователя на две части:\n"
            "1. 'search_target': что именно нужно искать.\n"
            "2. 'action': список что сделать с найденным.\n"
            "Ответь СТРОГО в формате JSON. Ничего не пиши, кроме JSON. "
            "Ответ оставь на русском. Не решай задачу, только классифицируй."
        )
    ),
    "embeddings": AiModelSettings(
        model_name="nomic-embed-text",
        api_type="ollama",
        base_url=os.getenv("OLLAMA_URL"),
    )
}