from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "auth_users" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "full_name" VARCHAR(120) NOT NULL,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "password_hash" TEXT NOT NULL,
    "role" VARCHAR(20) NOT NULL DEFAULT 'user',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_auth_users_email_b815df" ON "auth_users" ("email");
CREATE TABLE IF NOT EXISTS "form_templates" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "original_filename" VARCHAR(255) NOT NULL,
    "mime_type" VARCHAR(128),
    "file_blob" BYTEA NOT NULL,
    "extracted_text" TEXT,
    "fields_schema" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "oo_key_nonce" INT NOT NULL DEFAULT 0,
    "file_version" INT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS "form_submissions" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "answers" JSONB NOT NULL,
    "filled_file_blob" BYTEA,
    "filled_mime_type" VARCHAR(128),
    "filled_filename" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "template_id" INT NOT NULL REFERENCES "form_templates" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "auth_users" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmm1v2zYQx7+KwFcZ4AWJl7SGUQyQE2fN2tiD43Vth4GgpbNNhCJdkmpsZPnuBfVgyX"
    "pwrczxrMavEh95EvnjkfrfSQ/IEy4wdfynAona1gPixAPUtlbsDQuR2SyxGoMmIxZ0JL6e"
    "Yl+BDMxkpLQkjkZta0yYgoaFXFCOpDNNBUdti/uMGaNwlJaUTxKTz+kXH7AWE9DTYDR//9"
    "OwEOUuzEHFP2d3eEyBuSuDpa65d2DHejELbNdcXwUdzd1G2BHM93jSebbQU8GXvSnXxjoB"
    "DpJoMJfX0jfDN6OL5hrPKBxp0iUcYsrHhTHxmU5Nd0MGjuCGH+XaTPgBTcxdfm6enr0+a/"
    "3y6qzVsFAwkqXl9WM4vWTuoWNAoDdEj0E70STsEWBMuAV/c+QupkQWoxv7jOHYKUNQaZkl"
    "GPNahzA2JAyTuNkSRI/MMQM+0VPUtk6bJ2uQfbAHF2/twdFp8+QnMxshiROGeS9qaoZthm"
    "vCETxCWRWQS4ftQHz2OFxB2Dw/3wBh8/y8FGHQtopwRpS6F9LFU6KmeZRDmJds55xjXeJy"
    "DcNh9+PQDNpT6gtLozu6sT8GVL1F1PK+3/st7p5CffG+38kQloJV2uxx/93xROYxgrYWpp"
    "ts9DX7PL/NHQlmxpjoPMdLokFTD4pZrnpmiLqR63H8z37GK5JA3D5ni+h8WRe/1zfd26F9"
    "88dKEF/aw65paa4EcGw9epVZieVFrL+uh28t89P63O91A4JC6YkM7pj0G35GZkzE1wJzcY"
    "+JmzoKY2sM5tGIiXEkJpbqYkScu3siXbzSkkTAWEgPK3/kUaWo4CofB53oClfvBsBIwDi/"
    "4pG4uhLSu11ebD9XPVrlxBqvvsElmqIMYL7Ja3pZC+FkEoza3NvcqRhMgS7NoytXqEWLdt"
    "CpddKphKv7KMFYhff7bb9XTC/lkj1uqaOtfy1Gld7rLVeEysx3vTDIaoDMYWkukBUGY8oY"
    "uHhMGeARE6OCQ41yIhclOUGBd4b4aKFBbcA6isr9QN2J6C1Rf7AHneuePfhULMI6BbQ7n4"
    "Zdu5i2Rz0IAVXJvwp8nyTPdk86m4W1NsrCWmuysFZWnqUisXJim3etJddnSc0OsvcHkr3p"
    "hdXgzRjRgCvpkozX9wXKnqzjVjRKAs/kqtXApTxeErRcopUPwDzEKyGBTvg7CFXHNVeacK"
    "foYE4lBMPU5eqTSTUsJMn9MlvI7i/BsQsMdPgEs28v7MsuykXiFgjGpf76kkttsGJq5Sn+"
    "c2ezy9AsyWXTofudTDaOj0MeW7s8VlNdrQa7dKhLUXsHclRIOqGcsCcJ/ULnA9zkSHpKWn"
    "rIR8vy0ScWVP5zJWW/qlbPVUqBefDsAxdrmOsqLw3znjUJ212/NAyfYlg5U/BIlfprznH3"
    "VVj0ZuxzxxC2Rj5lmnJ1bO73K6pPbfZQe/lBay9C4DtYYC6inGxDMZ11210h4eT/ltWZB+"
    "tXkPGrvw3ZZd1eDLsnveo+vOV+7rfcNkjqTIsqAlHL+u8ukz6HGkCNagCl51Z5flV+Zr3k"
    "VNVsjQoQo+71BHh6stFXqydrvlo1bRltKbiGcA9uqupTLoevKlROuVd40G7/wfL4DSdNWk"
    "8="
)
