from sqlalchemy.orm import Session


def create_customer(db: Session, *, name: str, phone: str | None = None) -> dict:
    return {
        "status": "placeholder",
        "message": "Customer service will be implemented in Week 2.",
        "name": name,
        "phone": phone,
    }


def get_customer_by_name(db: Session, *, name: str) -> dict:
    return {
        "status": "placeholder",
        "message": "Customer lookup service will be implemented in Week 2.",
        "name": name,
    }
