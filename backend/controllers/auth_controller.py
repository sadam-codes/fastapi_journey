from fastapi import APIRouter, Depends, status

from helpers.auth_helper import get_current_user, login_user, require_roles, signup_user
from schemas.auth_schemas import LoginRequest, SignUpRequest
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: SignUpRequest):
    return await signup_user(payload)


@router.post("/login")
async def login(payload: LoginRequest):
    return await login_user(payload)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": user}


@router.get("/admin")
async def admin_only(
    user: dict = Depends(require_roles([User.ROLE_ADMIN])),
):
    return {"message": "Welcome admin", "user": user}


@router.get("/user")
async def user_only(
    user: dict = Depends(require_roles([User.ROLE_USER])),
):
    return {"message": "Welcome user", "user": user}
