from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_owner
from app.database import get_db
from app.models.shop_owner import ShopOwner
from app.services.analytics_service import get_shop_analytics
from app.services.transaction_service import list_due_today, list_overdue

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), current_owner: ShopOwner = Depends(get_current_owner)) -> dict:
    return get_shop_analytics(db, owner_id=current_owner.id)


@router.get("/due-today")
def due_today(db: Session = Depends(get_db), current_owner: ShopOwner = Depends(get_current_owner)) -> dict:
    return list_due_today(db, owner_id=current_owner.id)


@router.get("/overdue")
def overdue(db: Session = Depends(get_db), current_owner: ShopOwner = Depends(get_current_owner)) -> dict:
    return list_overdue(db, owner_id=current_owner.id)
