from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.services.customer_service import _compute_customer_stats, _find_customer_by_name


def add_credit(
    db: Session,
    *,
    customer_name: str,
    amount: float,
    note: str | None = None,
    due_date: str | None = None,
) -> dict:
    customer = _find_customer_by_name(db, customer_name)
    if customer is None:
        return {"error": f"Customer '{customer_name}' not found. Add the customer first."}

    parsed_amount = Decimal(str(amount))
    if parsed_amount <= 0:
        return {"error": "Amount must be greater than zero."}

    parsed_due_date: date | None = None
    if due_date:
        try:
            parsed_due_date = date.fromisoformat(due_date)
        except ValueError:
            return {"error": "Invalid due_date format. Use YYYY-MM-DD."}

    txn = Transaction(
        customer_id=customer.id,
        type="credit_given",
        amount=parsed_amount,
        note=note,
        due_date=parsed_due_date,
    )
    db.add(txn)
    db.commit()

    stats = _compute_customer_stats(db, customer)
    return {
        "success": True,
        "customer_name": customer.name,
        "amount_recorded": float(parsed_amount),
        "due_date": parsed_due_date.isoformat() if parsed_due_date else None,
        "new_balance": stats["balance"],
    }


def record_payment(
    db: Session,
    *,
    customer_name: str,
    amount: float,
    note: str | None = None,
) -> dict:
    customer = _find_customer_by_name(db, customer_name)
    if customer is None:
        return {"error": f"Customer '{customer_name}' not found."}

    parsed_amount = Decimal(str(amount))
    if parsed_amount <= 0:
        return {"error": "Amount must be greater than zero."}

    stats = _compute_customer_stats(db, customer)
    current_balance = Decimal(str(stats["balance"]))
    if parsed_amount > current_balance:
        return {
            "error": (
                f"Payment exceeds outstanding balance. Current balance for '{customer.name}' is "
                f"PKR {float(current_balance):.2f}."
            )
        }

    txn = Transaction(
        customer_id=customer.id,
        type="payment_received",
        amount=parsed_amount,
        note=note,
        due_date=None,
    )
    db.add(txn)
    db.commit()

    updated_stats = _compute_customer_stats(db, customer)
    return {
        "success": True,
        "customer_name": customer.name,
        "amount_recorded": float(parsed_amount),
        "remaining_balance": updated_stats["balance"],
    }
