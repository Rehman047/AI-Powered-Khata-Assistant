from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.customer_service import delete_customer, get_customer_history, get_customer_info, list_all_customers

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("/")
def list_customers(db: Session = Depends(get_db)) -> dict:
    return list_all_customers(db)


@router.get("/{name}/history")
def get_customer_history_endpoint(name: str, db: Session = Depends(get_db)) -> dict:
    return get_customer_history(db, customer_name=name)


@router.get("/{name}")
def get_customer(name: str, db: Session = Depends(get_db)) -> dict:
    return get_customer_info(db, customer_name=name)


@router.delete("/{name}")
def remove_customer(name: str, db: Session = Depends(get_db)) -> dict:
    return delete_customer(db, customer_name=name)
