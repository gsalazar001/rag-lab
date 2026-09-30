import os
import re

import psycopg
from psycopg import errors


DEFAULT_DSN = "dbname=rag_lab"
IDENTIFIER_PATTERN = re.compile(r"\b[A-Z]{2,}[A-Z0-9]*-[A-Z0-9-]+\b")


def get_database_dsn():
    return os.environ.get("RAG_DATABASE_URL") or os.environ.get("DATABASE_URL") or DEFAULT_DSN


def connect():
    return psycopg.connect(get_database_dsn())


def vector_literal(values):
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def extract_identifiers(query):
    return IDENTIFIER_PATTERN.findall(query.upper())


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
                operation TEXT,
                segment TEXT,
                content_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        cursor.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS country TEXT;")
        cursor.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS category TEXT;")
        cursor.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS operation TEXT;")
        cursor.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS segment TEXT;")
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
                SELECT id, source, country, category, operation, segment, content_hash
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
                "operation": None,
                "segment": None,
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
            "operation": row[4],
            "segment": row[5],
            "content_hash": row[6],
        }
        for row in rows
    ]


def insert_document(connection, source, country, category, operation, segment, content_hash):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO documents (source, country, category, operation, segment, content_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (source, country, category, operation, segment, content_hash),
        )
        return cursor.fetchone()[0]


def update_document(connection, document_id, country, category, operation, segment, content_hash):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE documents
            SET country = %s,
                category = %s,
                operation = %s,
                segment = %s,
                content_hash = %s,
                updated_at = now()
            WHERE id = %s;
            """,
            (country, category, operation, segment, content_hash, document_id),
        )


def build_filter_sql(country=None, category=None, operation=None, segment=None):
    where_clauses = []
    params = []

    if country:
        where_clauses.append("lower(documents.country) = lower(%s)")
        params.append(country)
    if category:
        where_clauses.append("lower(documents.category) = lower(%s)")
        params.append(category)
    if operation:
        where_clauses.append("lower(documents.operation) = lower(%s)")
        params.append(operation)
    if segment:
        where_clauses.append("lower(documents.segment) = lower(%s)")
        params.append(segment)

    if not where_clauses:
        return "", params

    return "WHERE " + " AND ".join(where_clauses), params


def count_chunks_for_document(connection, document_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM chunks WHERE document_id = %s;", (document_id,))
        return cursor.fetchone()[0]


def count_chunks(connection, country=None, category=None, operation=None, segment=None):
    where_sql, params = build_filter_sql(country, category, operation, segment)

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


def row_to_result(row, score_name):
    return {
        "id": row[0],
        "chunk_index": row[1],
        "text": row[2],
        "metadata": {
            "source": row[3],
            "country": row[4],
            "category": row[5],
            "operation": row[6],
            "segment": row[7],
        },
        score_name: row[8],
        "similarity": row[8] if score_name == "vector_score" else None,
    }


def vector_search_chunks(connection, query_embedding, top_k, country=None, category=None, operation=None, segment=None):
    query_vector = vector_literal(query_embedding)
    where_sql, filter_params = build_filter_sql(country, category, operation, segment)
    params = [query_vector] + filter_params + [query_vector, top_k]

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
                documents.operation,
                documents.segment,
                1 - (chunks.embedding <=> %s::vector) AS vector_score
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            {where_sql}
            ORDER BY chunks.embedding <=> %s::vector
            LIMIT %s;
            """,
            params,
        )
        rows = cursor.fetchall()

    return [row_to_result(row, "vector_score") for row in rows]


def text_search_chunks(connection, query, top_k, country=None, category=None, operation=None, segment=None):
    where_sql, filter_params = build_filter_sql(country, category, operation, segment)
    identifiers = extract_identifiers(query)
    exact_conditions = []
    exact_params = []

    for identifier in identifiers:
        exact_conditions.append("chunks.content ILIKE %s")
        exact_params.append(f"%{identifier}%")

    text_match_sql = "to_tsvector('simple', chunks.content) @@ websearch_to_tsquery('simple', %s)"
    combined_conditions = [text_match_sql]
    if exact_conditions:
        combined_conditions.append("(" + " OR ".join(exact_conditions) + ")")

    search_condition = "(" + " OR ".join(combined_conditions) + ")"
    if where_sql:
        where_sql = where_sql + " AND " + search_condition
    else:
        where_sql = "WHERE " + search_condition

    params = [query] + exact_params + filter_params + [query] + exact_params + [top_k]

    exact_score_sql = "0"
    if exact_conditions:
        exact_score_sql = "CASE WHEN " + " OR ".join(exact_conditions) + " THEN 1.0 ELSE 0.0 END"

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
                documents.operation,
                documents.segment,
                ts_rank(
                    to_tsvector('simple', chunks.content),
                    websearch_to_tsquery('simple', %s)
                ) + {exact_score_sql} AS text_score
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            {where_sql}
            ORDER BY text_score DESC
            LIMIT %s;
            """,
            params,
        )
        rows = cursor.fetchall()

    return [row_to_result(row, "text_score") for row in rows]


def reciprocal_rank_fusion(vector_results, text_results, top_k, k=60):
    combined = {}

    for rank, result in enumerate(vector_results, start=1):
        chunk_id = result["id"]
        combined.setdefault(chunk_id, {**result, "vector_rank": None, "text_rank": None, "rrf_score": 0.0})
        combined[chunk_id]["vector_rank"] = rank
        combined[chunk_id]["vector_score"] = result["vector_score"]
        combined[chunk_id]["rrf_score"] += 1 / (k + rank)

    for rank, result in enumerate(text_results, start=1):
        chunk_id = result["id"]
        combined.setdefault(chunk_id, {**result, "vector_rank": None, "text_rank": None, "rrf_score": 0.0})
        combined[chunk_id]["text_rank"] = rank
        combined[chunk_id]["text_score"] = result["text_score"]
        combined[chunk_id]["rrf_score"] += 1 / (k + rank)

    results = list(combined.values())
    results.sort(key=lambda item: item["rrf_score"], reverse=True)
    return results[:top_k]


def hybrid_search_chunks(connection, query, query_embedding, top_k, country=None, category=None, operation=None, segment=None):
    candidate_limit = max(top_k * 4, 10)
    vector_results = vector_search_chunks(
        connection,
        query_embedding,
        candidate_limit,
        country=country,
        category=category,
        operation=operation,
        segment=segment,
    )
    text_results = text_search_chunks(
        connection,
        query,
        candidate_limit,
        country=country,
        category=category,
        operation=operation,
        segment=segment,
    )
    hybrid_results = reciprocal_rank_fusion(vector_results, text_results, top_k)
    return vector_results, text_results, hybrid_results


def search_chunks(connection, query_embedding, top_k, country=None, category=None, operation=None, segment=None):
    return vector_search_chunks(
        connection,
        query_embedding,
        top_k,
        country=country,
        category=category,
        operation=operation,
        segment=segment,
    )
