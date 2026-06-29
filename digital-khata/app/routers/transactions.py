from fastapi import APIRouter

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/")
def list_transactions_placeholder() -> dict:
    return {"status": "ok", "message": "Transactions endpoint placeholder for Week 1."}
