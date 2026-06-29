from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import chat_with_tools

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/")
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    history = [item.model_dump() for item in payload.history]
    reply, updated_history = chat_with_tools(
        message=payload.message,
        history=history,
        db=db,
    )
    return ChatResponse(reply=reply, history=updated_history)
