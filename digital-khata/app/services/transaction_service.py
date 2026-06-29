from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session


def add_transaction(
    db: Session,
    *,
    customer_id: UUID,
    type: str,
    amount: Decimal,
    note: str | None = None,
    due_date: str | None = None,
) -> dict:
    return {
        "status": "placeholder",
        "message": "Transaction service will be implemented in Week 2.",
        "customer_id": str(customer_id),
        "type": type,
        "amount": str(amount),
        "note": note,
        "due_date": due_date,
    }
