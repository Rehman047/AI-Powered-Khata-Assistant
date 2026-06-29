from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransactionOut(BaseModel):
    id: UUID
    customer_id: UUID
    type: str
    amount: Decimal
    note: str | None
    due_date: date | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
