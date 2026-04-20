from pydantic import BaseModel

class AiModelSettings(BaseModel):
    model_name: str
    temperature: float = 0.2
    system_prompt: str
    endpoint: str 
    api_type: str
    base_url: str