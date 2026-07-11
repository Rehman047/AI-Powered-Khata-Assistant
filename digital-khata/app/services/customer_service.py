from datetime import date
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.transaction import Transaction
from app.services.trust_score import calculate_trust_score
from app.utils.token import generate_self_view_token, make_self_view_url


def _find_customer_by_name(db: Session, owner_id: UUIDType, name: str) -> Customer | None:
    normalized_name = name.strip().lower()
    return (
        db.query(Customer)
        .filter(Customer.owner_id == owner_id)
        .filter(func.lower(Customer.name) == normalized_name)
        .first()
    )


def _compute_customer_stats(db: Session, customer: Customer) -> dict:
    transactions = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer.id)
        .all()
    )

    total_credit_given = sum(
        (t.amount for t in transactions if t.type == "credit_given"),
        Decimal("0"),
    )
    total_payments_received = sum(
        (t.amount for t in transactions if t.type == "payment_received"),
        Decimal("0"),
    )
    outstanding_balance = total_credit_given - total_payments_received

    today = date.today()
    overdue_days = [
        (today - t.due_date).days
        for t in transactions
        if t.type == "credit_given" and t.due_date is not None and t.due_date < today
    ]
    overdue_count = len(overdue_days)
    max_days_past_due = max(overdue_days) if overdue_days else 0
    payment_count = sum(1 for t in transactions if t.type == "payment_received")

    trust = calculate_trust_score(
        total_credit_given=total_credit_given,
        total_payments_received=total_payments_received,
        outstanding_balance=outstanding_balance,
        overdue_count=overdue_count,
        max_days_past_due=max_days_past_due,
        payment_count=payment_count,
    )

    return {
        "total_credit_given": float(total_credit_given),
        "total_payments_received": float(total_payments_received),
        "balance": float(outstanding_balance),
        "overdue_count": overdue_count,
        "max_days_past_due": max_days_past_due,
        "payment_count": payment_count,
        "trust_score": trust.get("trust_score", 0),
        "trust_label": trust.get("trust_label", "Not rated"),
    }


def add_customer(db: Session, *, owner_id: UUIDType, name: str, phone: str | None = None) -> dict:
    existing_customer = _find_customer_by_name(db, owner_id, name)
    if existing_customer is not None:
        stats = _compute_customer_stats(db, existing_customer)
        return {
            "error": f"Customer '{existing_customer.name}' already exists.",
            "customer": {
                "id": str(existing_customer.id),
                "name": existing_customer.name,
                "phone": existing_customer.phone,
                **stats,
            },
        }

    customer = Customer(
        owner_id=owner_id,
        name=name.strip(),
        phone=phone,
        self_view_token=generate_self_view_token(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return {
        "success": True,
        "id": str(customer.id),
        "name": customer.name,
    }


def get_customer_info(db: Session, *, owner_id: UUIDType, customer_name: str) -> dict:
    customer = _find_customer_by_name(db, owner_id, customer_name)
    if customer is None:
        return {"error": f"Customer '{customer_name}' not found."}

    stats = _compute_customer_stats(db, customer)

    recent_transactions = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer.id)
        .order_by(Transaction.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "phone": customer.phone,
            "self_view_link": make_self_view_url(customer.self_view_token),
        },
        **stats,
        "recent_transactions": [
            {
                "type": txn.type,
                "amount": float(txn.amount),
                "note": txn.note,
                "due_date": txn.due_date.isoformat() if txn.due_date else None,
                "date": txn.created_at.date().isoformat(),
            }
            for txn in recent_transactions
        ],
    }


def get_customer_history(db: Session, *, owner_id: UUIDType, customer_name: str) -> dict:
    customer = _find_customer_by_name(db, owner_id, customer_name)
    if customer is None:
        return {"error": f"Customer '{customer_name}' not found."}

    stats = _compute_customer_stats(db, customer)

    transactions = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    return {
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "phone": customer.phone,
            "self_view_link": make_self_view_url(customer.self_view_token),
        },
        "balance": stats["balance"],
        "trust_score": stats["trust_score"],
        "trust_label": stats["trust_label"],
        "overdue_count": stats["overdue_count"],
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


def list_all_customers(db: Session, *, owner_id: UUIDType) -> dict:
    customers = db.query(Customer).filter(Customer.owner_id == owner_id).order_by(Customer.name.asc()).all()

    summaries = []
    for customer in customers:
        stats = _compute_customer_stats(db, customer)
        summaries.append(
            {
                "name": customer.name,
                "balance": stats["balance"],
                "trust_score": stats["trust_score"],
                "trust_label": stats["trust_label"],
                "overdue_count": stats["overdue_count"],
            }
        )

    return {
        "count": len(summaries),
        "customers": summaries,
    }


def delete_customer(db: Session, *, owner_id: UUIDType, customer_name: str) -> dict:
    customer = _find_customer_by_name(db, owner_id, customer_name)
    if customer is None:
        return {"error": f"Customer '{customer_name}' not found."}

    stats = _compute_customer_stats(db, customer)
    if stats["balance"] > 0:
        return {
            "error": (
                f"Cannot delete '{customer.name}'. Outstanding balance is PKR {stats['balance']:.2f}. "
                "Clear balance first."
            )
        }

    db.delete(customer)
    db.commit()

    return {
        "success": True,
        "message": f"Customer '{customer.name}' deleted.",
    }


def get_self_view_link(db: Session, *, owner_id: UUIDType, customer_name: str) -> dict:
    customer = _find_customer_by_name(db, owner_id, customer_name)
    if customer is None:
        return {"error": f"Customer '{customer_name}' not found."}

    return {
        "name": customer.name,
        "url": make_self_view_url(customer.self_view_token),
    }
