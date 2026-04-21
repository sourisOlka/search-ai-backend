from pydantic import BaseModel
from typing import Optional


class AiModelSettings(BaseModel):
    model_name: str
    temperature: float = 0.2
    system_prompt: Optional[str] = None 
    api_type: str
    base_url: str