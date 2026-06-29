from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/{customer_id}")
def list_transactions(customer_id: str, db: Session = Depends(get_db)) -> dict:
    transactions = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    return {
        "customer_id": customer_id,
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
