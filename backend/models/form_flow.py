from tortoise import fields
from tortoise.fields.base import CASCADE
from tortoise.models import Model


class FormTemplate(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    original_filename = fields.CharField(max_length=255)
    mime_type = fields.CharField(max_length=128, null=True)
    file_blob = fields.BinaryField()
    extracted_text = fields.TextField(null=True)
    fields_schema = fields.JSONField(default=list)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "form_templates"


class FormSubmission(Model):
    id = fields.IntField(pk=True)
    template = fields.ForeignKeyField(
        "models.FormTemplate",
        related_name="submissions",
        on_delete=CASCADE,
    )
    user = fields.ForeignKeyField(
        "models.User",
        related_name="form_submissions",
        on_delete=CASCADE,
    )
    answers = fields.JSONField()
    filled_file_blob = fields.BinaryField(null=True)
    filled_mime_type = fields.CharField(max_length=128, null=True)
    filled_filename = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "form_submissions"
