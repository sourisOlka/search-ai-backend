import httpx
from fastapi import HTTPException
from src.core.ai_config import AI_AGENTS

class AIService:
    async def generate(self, agent_id: str, user_query: str):
        agent = AI_AGENTS.get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Агент {agent_id} не найден")
        
        url = f"{agent.base_url}{agent.endpoint}"

        if agent.api_type == "ollama":
            payload = {
                "model": agent.model_name,
                "prompt": f"{agent.system_prompt}\n\nЗапрос: {user_query}",
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": agent.temperature
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"Тип API {agent.api_type} не поддерживается")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=120.0)
                response.raise_for_status()
                
                result = response.json()
                return result.get("response")
                
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"AI error: {e.response.text}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка подключения к AI: {str(e)}")


ai_service = AIService()