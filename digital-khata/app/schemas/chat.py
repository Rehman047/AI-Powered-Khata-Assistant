from typing import Literal

from pydantic import BaseModel


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage]


class ChatResponse(BaseModel):
    reply: str
    history: list[HistoryMessage]
