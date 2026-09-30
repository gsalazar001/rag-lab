import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentence_transformers import SentenceTransformer

from embedding_lab import MODEL_NAME
from local_index import TOP_K
from pg_store import (
    connect,
    count_chunks,
    hybrid_search_chunks,
    text_search_chunks,
    vector_search_chunks,
)


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_LLM_MODEL = "claude-3-5-haiku-20241022"


def build_context(results):
    context_parts = []

    for result in results:
        metadata = result["metadata"]
        source = metadata.get("source", "desconocido")
        country = metadata.get("country", "desconocido")
        category = metadata.get("category", "desconocido")
        operation = metadata.get("operation", "desconocido")
        segment = metadata.get("segment", "desconocido")
        context_parts.append(
            f"[CHUNK {result['chunk_index']} | DOCUMENTO {source} | "
            f"COUNTRY {country} | CATEGORY {category} | "
            f"OPERATION {operation} | SEGMENT {segment}]\n{result['text']}"
        )

    return "\n\n".join(context_parts)


def build_prompt(context, question):
    return f"""INSTRUCCIONES

Responde utilizando únicamente la información contenida
en CONTEXTO.

Si el contexto no contiene información suficiente para
responder, indica claramente que no encuentras esa información
en los documentos disponibles.

No inventes datos.

CONTEXTO

{context}

PREGUNTA

{question}
"""


def call_llm(prompt):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta la variable de entorno ANTHROPIC_API_KEY. "
            "Definila antes de ejecutar el RAG."
        )

    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_LLM_MODEL)
    payload = {
        "model": model,
        "max_tokens": 700,
        "temperature": 0,
        "system": "Responde de forma clara y breve. Usa solo el contexto provisto.",
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    request = Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        error_body = error.read().decode("utf-8")
        raise RuntimeError(f"Error HTTP del LLM: {error.code} {error_body}") from error
    except URLError as error:
        raise RuntimeError(f"Error de conexión con el LLM: {error}") from error

    data = json.loads(response_body)
    text_blocks = [block["text"] for block in data["content"] if block.get("type") == "text"]
    return "\n".join(text_blocks).strip()


def print_result_line(index, result, score_name):
    metadata = result["metadata"]
    print(f"{index}.")
    print(f"chunk: {result['chunk_index']}")
    print(f"source: {metadata.get('source', 'desconocido')}")
    print(f"country: {metadata.get('country', 'desconocido')}")
    print(f"category: {metadata.get('category', 'desconocido')}")
    print(f"operation: {metadata.get('operation', 'desconocido')}")
    print(f"segment: {metadata.get('segment', 'desconocido')}")
    print(f"{score_name}: {result.get(score_name, 0):.4f}")
    print()


def print_debug_results(vector_results, text_results, hybrid_results):
    print("=== VECTOR SEARCH ===")
    for index, result in enumerate(vector_results[:TOP_K], start=1):
        print_result_line(index, result, "vector_score")

    print("=== TEXT SEARCH ===")
    for index, result in enumerate(text_results[:TOP_K], start=1):
        print_result_line(index, result, "text_score")

    print("=== HYBRID SEARCH ===")
    for index, result in enumerate(hybrid_results, start=1):
        print(f"{index}.")
        print(f"chunk: {result['chunk_index']}")
        print(f"source: {result['metadata'].get('source', 'desconocido')}")
        print(f"country: {result['metadata'].get('country', 'desconocido')}")
        print(f"category: {result['metadata'].get('category', 'desconocido')}")
        print(f"operation: {result['metadata'].get('operation', 'desconocido')}")
        print(f"segment: {result['metadata'].get('segment', 'desconocido')}")
        print(f"vector_rank: {result.get('vector_rank')}")
        print(f"text_rank: {result.get('text_rank')}")
        print(f"rrf_score: {result.get('rrf_score', 0):.6f}")
        print()


def run_rag(question, debug=False, country=None, category=None, operation=None, segment=None, search="hybrid"):
    if debug:
        print("Generando únicamente embedding de la pregunta...")
    embedding_model = SentenceTransformer(MODEL_NAME)
    question_embedding = embedding_model.encode(question)
    embedding_dimensions = len(question_embedding)

    filters = {
        "country": country,
        "category": category,
        "operation": operation,
        "segment": segment,
    }

    with connect() as connection:
        total_chunks = count_chunks(connection)
        filtered_chunks = count_chunks(connection, **filters)

        if debug:
            print("SQL retrieval: filtros metadata -> vector search + text search -> RRF")

        vector_results, text_results, hybrid_results = hybrid_search_chunks(
            connection,
            question,
            question_embedding,
            TOP_K,
            **filters,
        )

        if search == "vector":
            results = vector_results[:TOP_K]
        elif search == "text":
            results = text_results[:TOP_K]
        else:
            results = hybrid_results

    context = build_context(results)
    prompt = build_prompt(context, question)

    if debug:
        print("=== DEBUG EDUCATIVO ===")
        print("QUESTION")
        print(question)
        print()
        print(f"Embedding dimension: {embedding_dimensions}")
        print(f"Search mode: {search}")
        print()
        print("FILTERS")
        active_filters = {key: value for key, value in filters.items() if value}
        if active_filters:
            for key, value in active_filters.items():
                print(f"{key} = {value}")
        else:
            print("sin filtros")
        print()
        print("CANDIDATE SPACE")
        print(f"chunks totales: {total_chunks}")
        print(f"chunks después del filtro: {filtered_chunks}")
        print()
        print_debug_results(vector_results, text_results, hybrid_results)
        print("Contexto completo enviado al LLM:")
        print("-" * 40)
        print(context)
        print()
        print("Prompt final:")
        print("-" * 40)
        print(prompt)
        print()

    answer = call_llm(prompt)

    if debug:
        print("Respuesta del LLM:")
        print("-" * 40)
        print(answer)
    else:
        print(f"Pregunta: {question}")
        print()
        print(f"Respuesta: {answer}")


def parse_args():
    parser = argparse.ArgumentParser(description="Minimal educational RAG pipeline.")
    parser.add_argument("--debug", action="store_true", help="Show retrieval context and final prompt.")
    parser.add_argument("--question", help="Question to ask without interactive input.")
    parser.add_argument("--country", help="Filter retrieval by document country metadata.")
    parser.add_argument("--category", help="Filter retrieval by document category metadata.")
    parser.add_argument("--operation", help="Filter retrieval by document operation metadata.")
    parser.add_argument("--segment", help="Filter retrieval by document segment metadata.")
    parser.add_argument(
        "--search",
        choices=["vector", "text", "hybrid"],
        default="hybrid",
        help="Retrieval strategy used to build LLM context.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    question = args.question or input("Pregunta: ").strip()

    if not question:
        print("No ingresaste una pregunta.")
        return

    try:
        run_rag(
            question,
            debug=args.debug,
            country=args.country,
            category=args.category,
            operation=args.operation,
            segment=args.segment,
            search=args.search,
        )
    except RuntimeError as error:
        print()
        print(f"ERROR: {error}")


if __name__ == "__main__":
    main()
