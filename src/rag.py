import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentence_transformers import SentenceTransformer

from embedding_lab import MODEL_NAME
from local_index import TOP_K
from pg_store import connect, search_chunks


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_LLM_MODEL = "claude-3-5-haiku-20241022"


def build_context(results):
    context_parts = []

    for result in results:
        source = result["metadata"].get("source", "desconocido")
        context_parts.append(
            f"[CHUNK {result['chunk_index']} | DOCUMENTO {source}]\n{result['text']}"
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


def run_rag(question, debug=False):
    if debug:
        print("Generando únicamente embedding de la pregunta...")
    embedding_model = SentenceTransformer(MODEL_NAME)
    question_embedding = embedding_model.encode(question)
    embedding_dimensions = len(question_embedding)

    if debug:
        print("SQL retrieval: búsqueda vectorial en PostgreSQL con pgvector (<=> cosine distance)")
    with connect() as connection:
        results = search_chunks(connection, question_embedding, TOP_K)

    context = build_context(results)
    prompt = build_prompt(context, question)

    if debug:
        print("=== DEBUG EDUCATIVO ===")
        print(f"Pregunta original: {question}")
        print(f"Embedding dimension: {embedding_dimensions}")
        print()

        print(f"TOP {TOP_K}")
        for result in results:
            source = result["metadata"].get("source", "desconocido")
            print(
                f"Chunk: {result['chunk_index']} | Document: {source} | "
                f"Similarity: {result['similarity']:.4f}"
            )
        print()

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
    return parser.parse_args()


def main():
    args = parse_args()
    question = args.question or input("Pregunta: ").strip()

    if not question:
        print("No ingresaste una pregunta.")
        return

    try:
        run_rag(question, debug=args.debug)
    except RuntimeError as error:
        print()
        print(f"ERROR: {error}")


if __name__ == "__main__":
    main()
