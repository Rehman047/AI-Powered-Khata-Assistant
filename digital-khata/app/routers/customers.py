from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_owner
from app.database import get_db
from app.models.shop_owner import ShopOwner
from app.services.customer_service import delete_customer, get_customer_history, get_customer_info, list_all_customers

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("/")
def list_customers(db: Session = Depends(get_db), current_owner: ShopOwner = Depends(get_current_owner)) -> dict:
    return list_all_customers(db, owner_id=current_owner.id)


@router.get("/{name}/history")
def get_customer_history_endpoint(name: str, db: Session = Depends(get_db), current_owner: ShopOwner = Depends(get_current_owner)) -> dict:
    return get_customer_history(db, owner_id=current_owner.id, customer_name=name)


@router.get("/{name}")
def get_customer(name: str, db: Session = Depends(get_db), current_owner: ShopOwner = Depends(get_current_owner)) -> dict:
    return get_customer_info(db, owner_id=current_owner.id, customer_name=name)


@router.delete("/{name}")
def remove_customer(name: str, db: Session = Depends(get_db), current_owner: ShopOwner = Depends(get_current_owner)) -> dict:
    return delete_customer(db, owner_id=current_owner.id, customer_name=name)
