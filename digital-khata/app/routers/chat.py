from fastapi import APIRouter

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/")
def chat_placeholder() -> dict:
    return {"status": "ok", "message": "Chat endpoint placeholder for Week 1."}
