from fastapi import APIRouter

router = APIRouter(prefix="/api/self-view", tags=["self-view"])


@router.get("/{token}")
def self_view_placeholder(token: str) -> dict:
    return {
        "status": "ok",
        "token": token,
        "message": "Self-view endpoint placeholder for Week 1.",
    }
