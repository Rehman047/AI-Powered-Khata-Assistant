from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    shop_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    shop_name: str
    email: str


class OwnerOut(BaseModel):
    id: UUID
    shop_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)
