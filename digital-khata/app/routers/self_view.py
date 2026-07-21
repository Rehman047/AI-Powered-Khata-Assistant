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
              <title>AI Ledger Assistant - Link Invalid</title>
              <link rel="stylesheet" href="/style.css" />
            </head>
            <body class="self-view-page">
              <main class="self-view-shell self-view-shell--invalid">
                <section class="self-view-card">
                  <div class="self-view-brand">AI Ledger Assistant</div>
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
    txn_data_js_rows = []
    for txn in transactions:
        amount_class = "transaction-row__amount--credit" if txn.type == "credit_given" else "transaction-row__amount--payment"
        amount_prefix = "+" if txn.type == "payment_received" else "-"
        label = "Payment" if txn.type == "payment_received" else "Credit"
        date_str = txn.created_at.strftime('%d %b %Y')
        note_str = txn.note or "—"
        rows.append(
            f"""
            <tr>
              <td>{escape(date_str)}</td>
              <td>{label}</td>
              <td class="{amount_class}">{amount_prefix}{_format_amount(float(txn.amount))}</td>
              <td>{escape(note_str)}</td>
            </tr>
            """
        )
        # Prepare JS-safe data for client-side download
        safe_date = date_str.replace("'", "\\'")
        safe_label = label.replace("'", "\\'")
        safe_amount = f"{amount_prefix}{float(txn.amount):.2f}"
        safe_note = note_str.replace("'", "\\'").replace("\\", "\\\\")
        txn_data_js_rows.append(
            f"  {{ date: '{safe_date}', type: '{safe_label}', amount: '{safe_amount}', note: '{safe_note}' }}"
        )

    trust_class = _trust_class(stats["trust_label"])
    history_rows = "\n".join(rows) if rows else """
      <tr><td colspan="4" class="empty-state">No transactions yet.</td></tr>
    """

    customer_name_js = escape(customer.name).replace("'", "\\'")
    txn_js_array = "[\n" + ",\n".join(txn_data_js_rows) + "\n]" if txn_data_js_rows else "[]"
    balance_val = f"{stats['balance']:.2f}"
    trust_label_js = escape(stats['trust_label']).replace("'", "\\'")
    trust_score_js = stats['trust_score']

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>AI Ledger Assistant - {escape(customer.name)}</title>
      <link rel="stylesheet" href="/style.css" />
      <style>
        /* ---- Download toolbar ---- */
        .download-toolbar {{
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          align-items: center;
          margin: 18px 0 4px;
        }}

        .download-toolbar .dl-label {{
          font-size: 0.8125rem;
          font-weight: 600;
          color: #c084fc;
          text-transform: uppercase;
          letter-spacing: 0.07em;
          flex: 0 0 auto;
        }}

        .dl-btn {{
          display: inline-flex;
          align-items: center;
          gap: 7px;
          padding: 9px 18px;
          border-radius: 8px;
          border: 1.5px solid #3b2166;
          background: #1c0e33;
          color: #f3e8ff;
          font-size: 0.8125rem;
          font-weight: 600;
          cursor: pointer;
          transition: background 160ms ease, border-color 160ms ease, transform 120ms ease, box-shadow 160ms ease;
          text-decoration: none;
          white-space: nowrap;
        }}

        .dl-btn:hover {{
          background: rgba(147,51,234,0.22);
          border-color: #a855f7;
          box-shadow: 0 0 12px rgba(168,85,247,0.28);
          transform: translateY(-1px);
        }}

        .dl-btn:active {{
          transform: translateY(0);
        }}

        .dl-btn--csv   {{ border-color: #2a6644; background: #0d2218; }}
        .dl-btn--csv:hover {{ background: rgba(34,197,94,0.18); border-color: #22c55e; box-shadow: 0 0 12px rgba(34,197,94,0.22); }}

        .dl-btn--json  {{ border-color: #1a3866; background: #071525; }}
        .dl-btn--json:hover {{ background: rgba(59,130,246,0.18); border-color: #3b82f6; box-shadow: 0 0 12px rgba(59,130,246,0.22); }}

        .dl-btn--print {{ border-color: #3b2166; background: #1c0e33; }}
        .dl-btn--print:hover {{ background: rgba(147,51,234,0.22); border-color: #a855f7; box-shadow: 0 0 12px rgba(168,85,247,0.28); }}

        .dl-btn svg {{
          flex-shrink: 0;
        }}

        /* Print only: hide download toolbar */
        @media print {{
          .download-toolbar {{ display: none !important; }}
          .self-view-footer {{ display: none; }}
        }}
      </style>
    </head>
    <body class="self-view-page">
      <main class="self-view-shell">
        <section class="self-view-card">
          <div class="self-view-brand">AI Ledger Assistant</div>
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

          <!-- Download Toolbar -->
          <div class="download-toolbar" role="group" aria-label="Download options">
            <span class="dl-label">⬇ Download as:</span>
            <button type="button" class="dl-btn dl-btn--csv" id="dlCsvBtn" title="Download transactions as CSV spreadsheet">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                <line x1="12" y1="12" x2="12" y2="18"/><polyline points="9 15 12 18 15 15"/>
              </svg>
              CSV
            </button>
            <button type="button" class="dl-btn dl-btn--json" id="dlJsonBtn" title="Download transactions as JSON file">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                <line x1="12" y1="12" x2="12" y2="18"/><polyline points="9 15 12 18 15 15"/>
              </svg>
              JSON
            </button>
            <button type="button" class="dl-btn dl-btn--print" id="dlPrintBtn" title="Print or save as PDF">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
                <rect x="6" y="14" width="12" height="8"/>
              </svg>
              Print / PDF
            </button>
          </div>

          <div class="table-wrap">
            <table class="self-view-table" id="txnTable">
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

      <script>
        (function () {{
          // ── Transaction data injected by server ──────────────────────
          var CUSTOMER_NAME = '{customer_name_js}';
          var BALANCE       = 'PKR {balance_val}';
          var TRUST_LABEL   = '{trust_label_js}';
          var TRUST_SCORE   = '{trust_score_js}';
          var TRANSACTIONS  = {txn_js_array};

          // ── Helpers ──────────────────────────────────────────────────
          function todayStr() {{
            return new Date().toLocaleDateString('en-PK', {{ day: '2-digit', month: 'short', year: 'numeric' }});
          }}

          function csvEscape(val) {{
            var s = String(val === undefined || val === null ? '' : val);
            if (s.includes(',') || s.includes('"') || s.includes('\\n')) {{
              return '"' + s.replace(/"/g, '""') + '"';
            }}
            return s;
          }}

          function triggerDownload(content, filename, mimeType) {{
            var blob = new Blob([content], {{ type: mimeType }});
            var url  = URL.createObjectURL(blob);
            var a    = document.createElement('a');
            a.href     = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            setTimeout(function () {{
              URL.revokeObjectURL(url);
              a.remove();
            }}, 500);
          }}

          function safeFilename(name) {{
            return name.replace(/[^a-zA-Z0-9_-]/g, '_');
          }}

          // ── CSV Download ─────────────────────────────────────────────
          document.getElementById('dlCsvBtn').addEventListener('click', function () {{
            var lines = [];
            lines.push('AI Ledger Assistant - Customer Statement');
            lines.push('Customer: ' + csvEscape(CUSTOMER_NAME));
            lines.push('Outstanding Balance: ' + csvEscape(BALANCE));
            lines.push('Trust Score: ' + csvEscape(TRUST_SCORE + ' - ' + TRUST_LABEL));
            lines.push('Downloaded on: ' + csvEscape(todayStr()));
            lines.push('');
            lines.push(['Date', 'Type', 'Amount (PKR)', 'Note'].map(csvEscape).join(','));
            TRANSACTIONS.forEach(function (t) {{
              lines.push([t.date, t.type, t.amount, t.note].map(csvEscape).join(','));
            }});
            if (!TRANSACTIONS.length) {{
              lines.push('No transactions yet.');
            }}
            var csv = lines.join('\\r\\n');
            triggerDownload(csv, 'statement_' + safeFilename(CUSTOMER_NAME) + '.csv', 'text/csv;charset=utf-8;');
          }});

          // ── JSON Download ─────────────────────────────────────────────
          document.getElementById('dlJsonBtn').addEventListener('click', function () {{
            var payload = {{
              customer_name: CUSTOMER_NAME,
              outstanding_balance: BALANCE,
              trust_score: TRUST_SCORE,
              trust_label: TRUST_LABEL,
              downloaded_on: todayStr(),
              transactions: TRANSACTIONS.map(function (t) {{
                return {{
                  date:   t.date,
                  type:   t.type,
                  amount: t.amount,
                  note:   t.note
                }};
              }})
            }};
            var json = JSON.stringify(payload, null, 2);
            triggerDownload(json, 'statement_' + safeFilename(CUSTOMER_NAME) + '.json', 'application/json');
          }});

          // ── Print / PDF ───────────────────────────────────────────────
          document.getElementById('dlPrintBtn').addEventListener('click', function () {{
            window.print();
          }});
        }})();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
