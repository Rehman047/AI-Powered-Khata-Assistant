from decimal import Decimal


def _get_trust_label(trust_score: int) -> str:
    if trust_score >= 80:
        return "Excellent"
    if trust_score >= 60:
        return "Good"
    if trust_score >= 40:
        return "Fair"
    if trust_score >= 20:
        return "Poor"
    return "High Risk"


def calculate_trust_score(
    *,
    total_credit_given: Decimal,
    total_payments_received: Decimal,
    outstanding_balance: Decimal,
    overdue_count: int,
    max_days_past_due: int,
    payment_count: int,
) -> dict:
    if total_credit_given == 0:
        return {
            "trust_score": 75,
            "trust_label": "New Customer",
        }

    score = 50.0

    repayment_ratio = total_payments_received / total_credit_given
    capped_ratio = min(Decimal("1.0"), repayment_ratio)
    score += float(capped_ratio) * 35.0

    overdue_count_penalty = min(25, overdue_count * 5)
    score -= overdue_count_penalty

    if max_days_past_due > 30:
        score -= 10
    elif max_days_past_due > 14:
        score -= 5

    payment_activity_bonus = min(10, payment_count * 2)
    score += payment_activity_bonus

    trust_score = max(0, min(100, round(score)))
    return {
        "trust_score": trust_score,
        "trust_label": _get_trust_label(trust_score),
    }
