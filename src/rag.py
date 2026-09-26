import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentence_transformers import SentenceTransformer

from embedding_lab import MODEL_NAME
from semantic_search import TOP_K, build_index, load_chunks, search


OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_LLM_MODEL = "gpt-4o-mini"


def build_context(results):
    context_parts = []

    for result in results:
        context_parts.append(f"[CHUNK {result['id']}]\n{result['text']}")

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
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta la variable de entorno OPENAI_API_KEY. "
            "Definila antes de ejecutar el RAG."
        )

    model = os.environ.get("OPENAI_MODEL", DEFAULT_LLM_MODEL)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Responde de forma clara y breve. Usa solo el contexto provisto.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }

    request = Request(
        OPENAI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
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
    return data["choices"][0]["message"]["content"].strip()


def run_rag(question, debug=False):
    chunks = load_chunks()
    embedding_model = SentenceTransformer(MODEL_NAME)
    index = build_index(chunks, embedding_model)

    results, comparison_count, embedding_dimensions = search(
        question,
        index,
        embedding_model,
        TOP_K,
    )

    context = build_context(results)
    prompt = build_prompt(context, question)

    if debug:
        print("=== DEBUG EDUCATIVO ===")
        print(f"Pregunta original: {question}")
        print(f"Número de chunks: {len(index)}")
        print(f"Dimensiones del embedding: {embedding_dimensions}")
        print(f"Comparaciones realizadas: {comparison_count}")
        print()

        print("Top-K recuperados:")
        for result in results:
            print(f"- Chunk ID: {result['id']} | Similarity: {result['similarity']:.4f}")
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
