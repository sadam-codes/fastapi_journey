from pydantic import BaseModel, EmailStr, field_validator

from models.user import User


class SignUpRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized_value = value.lower().strip()
        if normalized_value not in User.ALLOWED_ROLES:
            raise ValueError(
                f"Invalid role. Allowed roles: {', '.join(User.ALLOWED_ROLES)}"
            )
        return normalized_value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
