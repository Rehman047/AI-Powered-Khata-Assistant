from html import escape

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.services.customer_service import _compute_customer_stats

router = APIRouter(prefix="", tags=["self-view"])


def _format_amount(amount: float) -> str:
    return f"PKR {amount:,.2f}"


def _trust_class(trust_label: str) -> str:
    normalized = trust_label.lower()
    if normalized in {"excellent", "good"}:
        return "trust trust--positive"
    if normalized == "fair":
        return "trust trust--amber"
    if normalized in {"poor", "high risk"}:
        return "trust trust--negative"
    return "trust trust--neutral"


@router.get("/view/{token}", response_class=HTMLResponse)
def self_view(token: str, db: Session = Depends(get_db)) -> HTMLResponse:
    customer = db.query(Customer).filter(Customer.self_view_token == token).first()
    if customer is None:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1.0" />
              <title>Digital Khata - Link Invalid</title>
              <link rel="stylesheet" href="/style.css" />
            </head>
            <body class="self-view-page">
              <main class="self-view-shell self-view-shell--invalid">
                <section class="self-view-card">
                  <div class="self-view-brand">Digital Khata</div>
                  <h1>Link invalid or expired</h1>
                  <p>This balance link is no longer available. Please contact the shop owner for a fresh link.</p>
                </section>
              </main>
            </body>
            </html>
            """,
            status_code=200,
        )

    stats = _compute_customer_stats(db, customer)
    transactions = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    rows = []
    for txn in transactions:
        amount_class = "transaction-row__amount--credit" if txn.type == "credit_given" else "transaction-row__amount--payment"
        amount_prefix = "+" if txn.type == "payment_received" else "-"
        label = "Payment" if txn.type == "payment_received" else "Credit"
        rows.append(
            f"""
            <tr>
              <td>{escape(txn.created_at.strftime('%d %b %Y'))}</td>
              <td>{label}</td>
              <td class=\"{amount_class}\">{amount_prefix}{_format_amount(float(txn.amount))}</td>
              <td>{escape(txn.note or '—')}</td>
            </tr>
            """
        )

    trust_class = _trust_class(stats["trust_label"])
    history_rows = "\n".join(rows) if rows else """
      <tr><td colspan="4" class="empty-state">No transactions yet.</td></tr>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Digital Khata - {escape(customer.name)}</title>
      <link rel="stylesheet" href="/style.css" />
    </head>
    <body class="self-view-page">
      <main class="self-view-shell">
        <section class="self-view-card">
          <div class="self-view-brand">Digital Khata</div>
          <h1>{escape(customer.name)}</h1>
          <p class="self-view-subtitle">Read-only balance view shared by the shop owner.</p>

          <div class="self-view-balance-card">
            <span class="self-view-balance-label">Outstanding balance</span>
            <strong class="self-view-balance-value">{_format_amount(stats['balance'])}</strong>
          </div>

          <div class="{trust_class}">
            <span>{escape(stats['trust_label'])}</span>
            <strong>{stats['trust_score']}</strong>
          </div>
        </section>

        <section class="self-view-card">
          <h2>Transaction history</h2>
          <div class="table-wrap">
            <table class="self-view-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {history_rows}
              </tbody>
            </table>
          </div>
          <p class="self-view-footer">This page is read-only. Please contact the shop owner if anything looks incorrect.</p>
        </section>
      </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
