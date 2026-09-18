"""Authentication and role-based authorization dependencies."""

from typing import Iterable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.constants import Role
from app.core.security import decode_token
from app.db.session import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated. Sign in and send a bearer token.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise CREDENTIALS_ERROR

    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise CREDENTIALS_ERROR

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise CREDENTIALS_ERROR

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


def require_roles(*roles: Role):
    """Dependency factory: restrict an endpoint to the given roles."""
    allowed: Iterable[str] = {r.value for r in roles}

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Your account does not have access to this resource.",
            )
        return user

    return _guard


require_household = require_roles(Role.HOUSEHOLD)
require_hospital = require_roles(Role.HOSPITAL, Role.ADMIN)
require_admin = require_roles(Role.ADMIN)
require_collector = require_roles(Role.COLLECTOR, Role.ADMIN)
