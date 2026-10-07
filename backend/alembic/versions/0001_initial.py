"""Initial Cite schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-12
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE users (
            id UUID PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE sessions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE documents (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_url TEXT,
            file_path TEXT,
            status TEXT NOT NULL,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT documents_source_type CHECK (source_type IN ('text', 'url', 'file')),
            CONSTRAINT documents_status CHECK (status IN ('queued', 'ready', 'failed'))
        )
        """
    )
    op.execute("CREATE INDEX documents_user_created_idx ON documents (user_id, created_at DESC)")
    op.execute(
        """
        CREATE TABLE ingest_jobs (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ingest_jobs_status CHECK (status IN ('queued', 'running', 'ready', 'failed'))
        )
        """
    )
    op.execute("CREATE INDEX ingest_jobs_document_idx ON ingest_jobs (document_id)")
    op.execute(
        """
        CREATE TABLE chunks (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            heading TEXT,
            text TEXT NOT NULL,
            tsv tsvector GENERATED ALWAYS AS (
                to_tsvector('english', coalesce(heading, '') || ' ' || coalesce(text, ''))
            ) STORED,
            embedding vector(768),
            UNIQUE (document_id, position)
        )
        """
    )
    op.execute("CREATE INDEX chunks_user_id_idx ON chunks (user_id)")
    op.execute("CREATE INDEX chunks_tsv_gin ON chunks USING gin (tsv)")
    op.execute("CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)")
    op.execute(
        """
        CREATE TABLE questions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            refused BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX questions_user_created_idx ON questions (user_id, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS questions")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS ingest_jobs")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute("DROP TABLE IF EXISTS users")
