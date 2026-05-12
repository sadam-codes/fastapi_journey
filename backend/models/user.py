from tortoise import fields
from tortoise.models import Model


class User(Model):
    ROLE_ADMIN = "admin"
    ROLE_USER = "user"
    ALLOWED_ROLES = [ROLE_ADMIN, ROLE_USER]

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=120, source_field="full_name")
    email = fields.CharField(max_length=255, unique=True, index=True)
    password_hash = fields.TextField()
    role = fields.CharField(max_length=20, default=ROLE_USER)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "auth_users"
