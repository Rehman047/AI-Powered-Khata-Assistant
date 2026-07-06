from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import get_shop_analytics
from app.services.transaction_service import list_due_today, list_overdue

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics")
def analytics(db: Session = Depends(get_db)) -> dict:
    return get_shop_analytics(db)


@router.get("/due-today")
def due_today(db: Session = Depends(get_db)) -> dict:
    return list_due_today(db)


@router.get("/overdue")
def overdue(db: Session = Depends(get_db)) -> dict:
    return list_overdue(db)
