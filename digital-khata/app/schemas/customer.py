from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)


class CustomerOut(BaseModel):
    id: UUID
    name: str
    phone: str | None
    self_view_token: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
