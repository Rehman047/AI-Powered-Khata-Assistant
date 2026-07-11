from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_owner
from app.database import get_db
from app.models.shop_owner import ShopOwner
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import run_khata_chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_owner: ShopOwner = Depends(get_current_owner),
) -> ChatResponse:
    history = [item.model_dump() for item in payload.history]
    result = await run_khata_chat(
        message=payload.message,
        history=history,
        db_session=db,
        owner_id=current_owner.id,
    )
    return ChatResponse(reply=result["reply"], history=result["history"])
