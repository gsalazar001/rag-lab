import os

import psycopg


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
                content_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
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


def get_document_by_source(connection, source):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, source, content_hash FROM documents WHERE source = %s;",
            (source,),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "source": row[1],
        "content_hash": row[2],
    }


def insert_document(connection, source, content_hash):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO documents (source, content_hash)
            VALUES (%s, %s)
            RETURNING id;
            """,
            (source, content_hash),
        )
        return cursor.fetchone()[0]


def update_document_hash(connection, document_id, content_hash):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE documents
            SET content_hash = %s, updated_at = now()
            WHERE id = %s;
            """,
            (content_hash, document_id),
        )


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


def search_chunks(connection, query_embedding, top_k):
    query_vector = vector_literal(query_embedding)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                chunks.id,
                chunks.chunk_index,
                chunks.content,
                documents.source,
                1 - (chunks.embedding <=> %s::vector) AS similarity
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            ORDER BY chunks.embedding <=> %s::vector
            LIMIT %s;
            """,
            (query_vector, query_vector, top_k),
        )
        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "chunk_index": row[1],
            "text": row[2],
            "metadata": {"source": row[3]},
            "similarity": row[4],
        }
        for row in rows
    ]
