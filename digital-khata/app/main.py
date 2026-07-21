from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.models import customer, shop_owner, transaction  # noqa: F401
from app.routers import analytics, auth, chat, customers, self_view, transactions


app = FastAPI(title="AI Ledger Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(self_view.router)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
