from pydantic import BaseModel
from datetime import datetime

class FavoriteStatus(BaseModel):
    is_favorite: bool

class FavoritePropertyResponse(BaseModel):
    id: int
    user_id: int
    property_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class FavoriteBankruptcyResponse(BaseModel):
    id: int
    user_id: int
    bankruptcy_id: int
    created_at: datetime

    class Config:
        from_attributes = True
