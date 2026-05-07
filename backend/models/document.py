from tortoise import fields
from tortoise.fields.base import CASCADE
from tortoise.models import Model


class Document(Model):
    id = fields.IntField(pk=True)
    original_filename = fields.CharField(max_length=255)
    mime_type = fields.CharField(max_length=128, null=True)
    char_count = fields.IntField(default=0)
    file_blob = fields.BinaryField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "rag_documents"


class DocumentChunk(Model):
    id = fields.IntField(pk=True)
    document = fields.ForeignKeyField(
        "models.Document",
        related_name="chunks",
        on_delete=CASCADE,
    )
    chunk_index = fields.IntField()
    text = fields.TextField()
    embedding = fields.JSONField(null=True)

    class Meta:
        table = "rag_document_chunks"
