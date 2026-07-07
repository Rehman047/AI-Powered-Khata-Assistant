from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.transaction import Transaction
from app.services.customer_service import _compute_customer_stats


def get_shop_analytics(db: Session) -> dict:
    today = date.today()
    try:
        customers = db.query(Customer).all()

        total_customers = len(customers)
        customers_with_balance = 0
        total_outstanding = Decimal("0")
        overdue_customer_count = 0

        for customer in customers:
            stats = _compute_customer_stats(db, customer)
            balance = Decimal(str(stats["balance"]))

            if balance > 0:
                customers_with_balance += 1
                total_outstanding += balance

                if stats["overdue_count"] > 0:
                    overdue_customer_count += 1

        overdue_credit_rows = (
            db.query(Transaction)
            .filter(
                Transaction.type == "credit_given",
                Transaction.due_date.is_not(None),
                Transaction.due_date < today,
            )
            .all()
        )
        total_overdue_amount = sum((row.amount for row in overdue_credit_rows), Decimal("0"))

        average_debt = (
            (total_outstanding / customers_with_balance)
            if customers_with_balance > 0
            else Decimal("0")
        )

        return {
            "total_customers": total_customers,
            "customers_with_balance": customers_with_balance,
            "total_outstanding": float(total_outstanding),
            "average_debt": float(average_debt),
            "overdue_customer_count": overdue_customer_count,
            # Gross approximation: payments are not linked to individual credits.
            "total_overdue_amount": float(total_overdue_amount),
        }
    except Exception as exc:  # pragma: no cover
        return {
            "total_customers": 0,
            "customers_with_balance": 0,
            "total_outstanding": 0.0,
            "average_debt": 0.0,
            "overdue_customer_count": 0,
            "total_overdue_amount": 0.0,
            "error": f"Failed to compute shop analytics: {str(exc)}",
        }


def get_dashboard_metrics(db: Session) -> dict:
    # Backward-compatible alias.
    return get_shop_analytics(db)
