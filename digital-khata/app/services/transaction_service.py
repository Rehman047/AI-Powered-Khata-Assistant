from datetime import date
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.transaction import Transaction
from app.services.customer_service import _compute_customer_stats, _find_customer_by_name


def add_credit(
    db: Session,
    *,
    owner_id: UUIDType,
    customer_name: str,
    amount: float,
    note: str | None = None,
    due_date: str | None = None,
) -> dict:
    customer = _find_customer_by_name(db, owner_id, customer_name)
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
    owner_id: UUIDType,
    customer_name: str,
    amount: float,
    note: str | None = None,
) -> dict:
    customer = _find_customer_by_name(db, owner_id, customer_name)
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


def list_due_today(db: Session, *, owner_id: UUIDType) -> dict:
    today = date.today()
    try:
        due_credit_rows = (
            db.query(Transaction)
            .join(Customer)
            .filter(
                Customer.owner_id == owner_id,
                Transaction.type == "credit_given",
                Transaction.due_date == today,
            )
            .all()
        )

        customer_ids = {row.customer_id for row in due_credit_rows}
        due_today: list[dict] = []

        for customer_id in customer_ids:
            customer = db.query(Customer).filter(Customer.id == customer_id, Customer.owner_id == owner_id).first()
            if customer is None:
                continue

            stats = _compute_customer_stats(db, customer)
            if stats["balance"] <= 0:
                continue

            due_today.append(
                {
                    "name": customer.name,
                    "phone": customer.phone,
                    "balance": float(stats["balance"]),
                    "trust_score": stats["trust_score"],
                }
            )

        return {
            "date": today.isoformat(),
            "due_today": due_today,
            "count": len(due_today),
        }
    except Exception as exc:  # pragma: no cover
        return {
            "date": today.isoformat(),
            "due_today": [],
            "count": 0,
            "error": f"Failed to fetch due-today customers: {str(exc)}",
        }


def list_overdue(db: Session, *, owner_id: UUIDType) -> dict:
    today = date.today()
    try:
        overdue_credit_rows = (
            db.query(Transaction)
            .join(Customer)
            .filter(
                Customer.owner_id == owner_id,
                Transaction.type == "credit_given",
                Transaction.due_date.is_not(None),
                Transaction.due_date < today,
            )
            .all()
        )

        customer_ids = {row.customer_id for row in overdue_credit_rows}
        overdue: list[dict] = []

        for customer_id in customer_ids:
            customer = db.query(Customer).filter(Customer.id == customer_id, Customer.owner_id == owner_id).first()
            if customer is None:
                continue

            stats = _compute_customer_stats(db, customer)
            if stats["balance"] <= 0:
                continue

            customer_overdue_dates = [
                row.due_date
                for row in overdue_credit_rows
                if row.customer_id == customer_id and row.due_date is not None
            ]
            if not customer_overdue_dates:
                continue

            oldest_due_date = min(customer_overdue_dates)
            days_overdue = (today - oldest_due_date).days

            overdue.append(
                {
                    "name": customer.name,
                    "phone": customer.phone,
                    "balance": float(stats["balance"]),
                    "days_overdue": int(days_overdue),
                    "trust_score": stats["trust_score"],
                    "trust_label": stats["trust_label"],
                }
            )

        overdue.sort(key=lambda item: item["days_overdue"], reverse=True)

        return {
            "overdue": overdue,
            "count": len(overdue),
        }
    except Exception as exc:  # pragma: no cover
        return {
            "overdue": [],
            "count": 0,
            "error": f"Failed to fetch overdue customers: {str(exc)}",
        }
