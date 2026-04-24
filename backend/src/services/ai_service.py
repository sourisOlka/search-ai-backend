from fastapi import HTTPException
from src.core.ai_config import AI_AGENTS
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
import json
import asyncio


class AIService:
    async def analize(self, agent_id: str, user_query: str):
        agent = AI_AGENTS.get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Агент не найден")

        llm = ChatOllama(
            model=agent.model_name,
            base_url=agent.base_url,
            temperature=agent.temperature,
            format="json"
        )

        messages = [
            SystemMessage(content=agent.system_prompt),
            HumanMessage(content=user_query)
        ]

        try:
            response = await asyncio.wait_for(llm.ainvoke(messages), timeout=200.0)
        except asyncio.TimeoutError:
            return {"error": "Ollama timeout"}
        
        try:
            return json.loads(response.content)
        except:
            return response.content
        

    def get_embeddings(self):
        agent = AI_AGENTS.get("embeddings")
        if not agent:
            raise HTTPException(status_code=404, detail="Настройки эмбеддингов не найдены")
        
        if agent.api_type == "ollama":
            return OllamaEmbeddings(
                model=agent.model_name,
                base_url=agent.base_url
            )
        else:
            raise HTTPException(status_code=400, detail=f"Тип API {agent.api_type} для эмбеддингов не поддерживается")        

ai_service = AIService()