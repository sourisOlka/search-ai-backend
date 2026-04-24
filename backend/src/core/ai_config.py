from src.schemas.ai_model import AiModelSettings
import os, json
from src.core.ai_scheme import UI_WIDGETS
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR")
ACTIONS_GUIDE = "\n".join([
    f"- '{name}': {info['description']}" 
    for name, info in UI_WIDGETS.items()
])
SCHEMAS_GUIDE = "\n".join([
    f"Для компонента '{name}': используй структуру JSON: {json.dumps(info['schema'], ensure_ascii=False)}" 
    for name, info in UI_WIDGETS.items()
])

AI_AGENTS = {
    "classifier": AiModelSettings(
        model_name="llama3",
        api_type = "ollama",
        base_url = os.getenv("OLLAMA_URL"),
        temperature=0.1,
        system_prompt=(
            "Ты — эксперт-аналитик. Твоя задача — подготовить данные для поиска и выбрать формат отображения.\n\n"
            "Разбери запрос на две части:\n"
            "1. 'search_target': Это то, что хочет узнать пользователь. Напиши ОДНО-ДВА предложения, которые могли бы быть ответом "
            "на вопрос пользователя и сам вопрос. СТРОГО на русском языке.\n\n"
            "2. 'action': Выбери наиболее подходящий тип компонента соответствующий действию, которое пользователь хочет получить с ответом СТРОГО из списка доступных:\n"
            f"{ACTIONS_GUIDE}\n\n"
            "Если не подходит не под один из типов, выбирай 'RichText'.\n\n"
            "Формат ответа: СТРОГО JSON с полями 'search_target' и 'action'."
        )
    ),
    "create_scheme": AiModelSettings(
        model_name="llama3",
        api_type="ollama",
        base_url=os.getenv("OLLAMA_URL"),
        temperature=0.4,
        system_prompt=(
            "Ты — универсальный аналитик-исполнитель. Твоя задача: выполнить инструкцию пользователя, "
            "используя предоставленные фрагменты текста и строго следуя заданной схеме данных.\n\n"
            
            "ДОСТУПНЫЕ СХЕМЫ ДАННЫХ:\n"
            f"{SCHEMAS_GUIDE}\n\n"
            
            "ПРАВИЛА:\n"
            "1. Используй ТОЛЬКО факты из предоставленного текста.\n"
            "2. Выбери схему, которую указал классификатор (action), и заполни её данными.\n"
            "3. Если нужно составить тест (Quiz) — делай сильные дистракторы (правдоподобные, но неверные ответы).\n"
            "4. Формат ответа — СТРОГО JSON вида: {'component': 'Name', 'props': {...}}.\n\n"
            "Никакого лишнего текста, только чистый JSON. Ответ на русском языке."
        )
    ),
    "embeddings": AiModelSettings(
        model_name="nomic-embed-text",
        api_type="ollama",
        base_url=os.getenv("OLLAMA_URL"),
    )
}