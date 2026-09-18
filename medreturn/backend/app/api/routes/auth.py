"""Authentication: register, login, profile.

Registration creates household accounts only. Hospital, collector and
admin accounts are provisioned through scripts/create_user.py by someone
with database access, so the public endpoint cannot mint privilege.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.constants import Role
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Credit, User
from app.schemas import (
    LoginIn,
    ProfileUpdateIn,
    RegisterIn,
    TokenOut,
    UserWithAddressOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(str(user.id), user.role),
        user=UserWithAddressOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    existing = db.execute(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.email.lower())
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="That username or email is already registered. Sign in instead.",
        )

    user = User(
        username=payload.username,
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        address=payload.address.strip(),
        password_hash=hash_password(payload.password),
        role=Role.HOUSEHOLD.value,
    )
    db.add(user)
    db.flush()

    db.add(Credit(user_id=user.id, balance=0, lifetime_earned=0))
    db.commit()
    db.refresh(user)
    return _issue(user)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    identifier = payload.username.strip().lower()
    user = db.execute(
        select(User).where(or_(User.username == identifier, User.email == identifier))
    ).scalar_one_or_none()

    # Same message either way, so the endpoint does not confirm which
    # usernames exist.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Username or password is incorrect.",
        )
    if not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="This account is disabled. Contact support.",
        )
    return _issue(user)


@router.get("/me", response_model=UserWithAddressOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserWithAddressOut)
def update_me(
    payload: ProfileUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.address is not None:
        user.address = payload.address.strip()
    db.commit()
    db.refresh(user)
    return user
