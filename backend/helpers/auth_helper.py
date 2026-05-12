import bcrypt
import os
from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
from dotenv import load_dotenv

from fastapi import Depends, Header, HTTPException, status

from schemas.auth_schemas import LoginRequest, SignUpRequest
from models.user import User

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_password_valid(stored_password_hash: str, incoming_password: str) -> bool:
    return bcrypt.checkpw(incoming_password.encode("utf-8"), stored_password_hash.encode("utf-8"))


def create_access_token(user_id: int, email: str, role: str) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is missing in environment variables.")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _extract_token_from_auth_header(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )
    auth_parts = authorization.split(" ")
    if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use 'Bearer <token>'.",
        )
    return auth_parts[1]


def decode_access_token(token: str) -> dict:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is missing in environment variables.")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if "sub" not in payload or "email" not in payload or "role" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
            )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        ) from exc


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    token = _extract_token_from_auth_header(authorization)
    return decode_access_token(token)


def require_roles(allowed_roles: list[str]) -> Callable:
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role '{user.get('role')}'.",
            )
        return user

    return role_checker


async def signup_user(payload: SignUpRequest) -> dict:
    existing_user = await User.filter(email=payload.email.lower()).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered.")

    password_hash = hash_password(payload.password)

    user = await User.create(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=password_hash,
        role=User.ROLE_USER,
    )

    token = create_access_token(user.id, user.email, user.role)
    return {
        "message": "Signup successful",
        "token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at,
        },
    }


async def login_user(payload: LoginRequest) -> dict:
    user = await User.filter(email=payload.email.lower()).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not is_password_valid(user.password_hash, payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user.id, user.email, user.role)
    return {
        "message": "Login successful",
        "token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
    }
