from decimal import Decimal


def calculate_trust_score(
    *,
    total_credit_given: Decimal,
    total_payments_received: Decimal,
    outstanding_balance: Decimal,
    overdue_count: int,
    max_days_past_due: int,
    payment_count: int,
) -> dict:
    """Week 2 placeholder: returns neutral trust values until Week 4 formula is added."""
    _ = (
        total_credit_given,
        total_payments_received,
        outstanding_balance,
        overdue_count,
        max_days_past_due,
        payment_count,
    )
    return {
        "trust_score": 0,
        "trust_label": "Not rated",
    }
