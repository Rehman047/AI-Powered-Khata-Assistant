from sqlalchemy.orm import Session


def get_dashboard_metrics(db: Session) -> dict:
    return {
        "status": "placeholder",
        "message": "Analytics service will be implemented in Week 3.",
        "data": {
            "total_customers": 0,
            "customers_with_balance": 0,
            "total_outstanding": "0.00",
            "average_debt": "0.00",
            "overdue_customer_count": 0,
            "total_overdue_amount": "0.00",
        },
    }
