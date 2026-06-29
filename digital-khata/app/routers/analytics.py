from fastapi import APIRouter

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/")
def analytics_placeholder() -> dict:
    return {"status": "ok", "message": "Analytics endpoint placeholder for Week 1."}
