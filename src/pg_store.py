import os

import psycopg
from psycopg import errors


DEFAULT_DSN = "dbname=rag_lab"


def get_database_dsn():
    return os.environ.get("RAG_DATABASE_URL") or os.environ.get("DATABASE_URL") or DEFAULT_DSN


def connect():
    return psycopg.connect(get_database_dsn())


def vector_literal(values):
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def ensure_schema(connection, embedding_dimension):
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id BIGSERIAL PRIMARY KEY,
                source TEXT NOT NULL UNIQUE,
                country TEXT,
                category TEXT,
                content_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        cursor.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS country TEXT;")
        cursor.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS category TEXT;")
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector({embedding_dimension}) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (document_id, chunk_index)
            );
            """
        )


def list_documents(connection):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, source, country, category, content_hash
                FROM documents
                ORDER BY source;
                """
            )
            rows = cursor.fetchall()
    except errors.UndefinedTable:
        connection.rollback()
        return []
    except errors.UndefinedColumn:
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, source, content_hash
                FROM documents
                ORDER BY source;
                """
            )
            rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "source": row[1],
                "country": None,
                "category": None,
                "content_hash": row[2],
            }
            for row in rows
        ]

    return [
        {
            "id": row[0],
            "source": row[1],
            "country": row[2],
            "category": row[3],
            "content_hash": row[4],
        }
        for row in rows
    ]


def insert_document(connection, source, country, category, content_hash):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO documents (source, country, category, content_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (source, country, category, content_hash),
        )
        return cursor.fetchone()[0]


def update_document(connection, document_id, country, category, content_hash):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE documents
            SET country = %s,
                category = %s,
                content_hash = %s,
                updated_at = now()
            WHERE id = %s;
            """,
            (country, category, content_hash, document_id),
        )


def count_chunks_for_document(connection, document_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM chunks WHERE document_id = %s;", (document_id,))
        return cursor.fetchone()[0]


def count_chunks(connection, country=None, category=None):
    where_clauses = []
    params = []

    if country:
        where_clauses.append("documents.country = %s")
        params.append(country)
    if category:
        where_clauses.append("documents.category = %s")
        params.append(category)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            {where_sql};
            """,
            params,
        )
        return cursor.fetchone()[0]


def delete_document(connection, document_id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM documents WHERE id = %s;", (document_id,))


def delete_chunks_for_document(connection, document_id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM chunks WHERE document_id = %s;", (document_id,))


def insert_chunks(connection, document_id, chunks, embeddings):
    with connection.cursor() as cursor:
        for chunk_index, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
            cursor.execute(
                """
                INSERT INTO chunks (document_id, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s::vector);
                """,
                (document_id, chunk_index, chunk, vector_literal(embedding)),
            )


def search_chunks(connection, query_embedding, top_k, country=None, category=None):
    query_vector = vector_literal(query_embedding)
    where_clauses = []
    params = [query_vector]

    if country:
        where_clauses.append("documents.country = %s")
        params.append(country)
    if category:
        where_clauses.append("documents.category = %s")
        params.append(category)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    params.extend([query_vector, top_k])

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                chunks.id,
                chunks.chunk_index,
                chunks.content,
                documents.source,
                documents.country,
                documents.category,
                1 - (chunks.embedding <=> %s::vector) AS similarity
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            {where_sql}
            ORDER BY chunks.embedding <=> %s::vector
            LIMIT %s;
            """,
            params,
        )
        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "chunk_index": row[1],
            "text": row[2],
            "metadata": {
                "source": row[3],
                "country": row[4],
                "category": row[5],
            },
            "similarity": row[6],
        }
        for row in rows
    ]
