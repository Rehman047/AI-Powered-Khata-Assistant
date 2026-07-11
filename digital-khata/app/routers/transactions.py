from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.auth import get_current_owner
from app.database import get_db
from app.models.customer import Customer
from app.models.shop_owner import ShopOwner
from app.models.transaction import Transaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/{customer_id}")
def list_transactions(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_owner: ShopOwner = Depends(get_current_owner),
) -> dict:
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.owner_id == current_owner.id)
        .first()
    )
    if customer is None:
        return {"customer_id": str(customer_id), "count": 0, "transactions": []}

    transactions = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    return {
        "customer_id": str(customer_id),
        "count": len(transactions),
        "transactions": [
            {
                "id": str(txn.id),
                "type": txn.type,
                "amount": float(txn.amount),
                "note": txn.note,
                "due_date": txn.due_date.isoformat() if txn.due_date else None,
                "created_at": txn.created_at.isoformat(),
            }
            for txn in transactions
        ],
    }
