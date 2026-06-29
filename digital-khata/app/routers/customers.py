from fastapi import APIRouter

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("/")
def list_customers_placeholder() -> dict:
    return {"status": "ok", "message": "Customers endpoint placeholder for Week 1."}
