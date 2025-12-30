from pydantic import BaseModel
from typing import Optional, List, Any

class Miniature(BaseModel):
    id: Optional[int] = None
    name: str
    line: Optional[str] = None
    set_name: Optional[str] = None
    number: Optional[str] = None
    rarity: Optional[str] = None
    size: Optional[str] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    vision_description: Optional[str] = None
    embedding: Optional[List[float]] = None

    class Config:
        from_attributes = True
