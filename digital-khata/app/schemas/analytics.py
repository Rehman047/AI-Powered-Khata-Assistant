from decimal import Decimal

from pydantic import BaseModel


class AnalyticsOut(BaseModel):
    total_customers: int
    customers_with_balance: int
    total_outstanding: Decimal
    average_debt: Decimal
    overdue_customer_count: int
    total_overdue_amount: Decimal
