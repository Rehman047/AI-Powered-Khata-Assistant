from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_owner
from app.database import get_db
from app.models.shop_owner import ShopOwner
from app.schemas.auth import LoginRequest, OwnerOut, RegisterRequest, TokenResponse
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing_owner = db.query(ShopOwner).filter(ShopOwner.email == payload.email).first()
    if existing_owner is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    owner = ShopOwner(
        shop_name=payload.shop_name.strip(),
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    access_token = create_access_token(str(owner.id))
    return TokenResponse(
        access_token=access_token,
        shop_name=owner.shop_name,
        email=owner.email,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    owner = db.query(ShopOwner).filter(ShopOwner.email == payload.email).first()
    if owner is None or not verify_password(payload.password, owner.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(str(owner.id))
    return TokenResponse(
        access_token=access_token,
        shop_name=owner.shop_name,
        email=owner.email,
    )


@router.get("/me", response_model=OwnerOut)
def me(current_owner: ShopOwner = Depends(get_current_owner)) -> OwnerOut:
    return OwnerOut.model_validate(current_owner)
