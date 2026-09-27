import json
from pathlib import Path

import numpy as np


INDEX_PATH = Path(__file__).resolve().parent.parent / "storage" / "index.json"
TOP_K = 3


def cosine_similarity(vector_a, vector_b):
    vector_a = np.array(vector_a)
    vector_b = np.array(vector_b)

    dot_product = np.dot(vector_a, vector_b)
    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)

    return dot_product / (norm_a * norm_b)


def load_index(index_path=INDEX_PATH):
    if not index_path.exists():
        raise RuntimeError(
            f"No existe {index_path}. Ejecutá primero: python src/index_documents.py"
        )

    with index_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_index(records, index_path=INDEX_PATH):
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with index_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


def search_records(question_embedding, records, top_k=TOP_K):
    results = []

    for record in records:
        similarity = cosine_similarity(question_embedding, record["embedding"])
        results.append(
            {
                "id": record["id"],
                "text": record["text"],
                "metadata": record.get("metadata", {}),
                "similarity": similarity,
            }
        )

    results.sort(key=lambda item: item["similarity"], reverse=True)
    return results[:top_k], len(results)
