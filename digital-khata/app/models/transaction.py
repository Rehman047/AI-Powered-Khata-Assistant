from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("type IN ('credit_given', 'payment_received')", name="ck_transactions_type"),
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )

    id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    customer_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    customer = relationship("Customer", back_populates="transactions")


Index("ix_transactions_customer_id", Transaction.customer_id)
Index(
    "ix_transactions_due_date_credit_given",
    Transaction.due_date,
    postgresql_where=text("type = 'credit_given' AND due_date IS NOT NULL"),
)
