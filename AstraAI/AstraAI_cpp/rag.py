import json
import os
import numpy as np
from typing import List, Dict, Any, Optional, Callable

def load_all_rag_metadata(rag_dir: str):
    metadata = []

    json_files = sorted(f for f in os.listdir(rag_dir) if f.endswith(".json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {rag_dir}")

    for jf in json_files:
        path = os.path.join(rag_dir, jf)
        with open(path, "r") as f:
            data = json.load(f)

        chunks = data["chunks"] if isinstance(data, dict) else data

        for chunk in chunks:
            emb = chunk.get("embedding")
            if emb is None:
                continue
            if isinstance(emb, str):
                emb = json.loads(emb)

            chunk["embedding"] = np.array(emb, dtype=np.float64)
            metadata.append(chunk)

    BLUE = "\033[94m"
    RED = "\033[91m"
    RESET = "\033[0m"
    print(f"{RED}[RAG] Loaded {len(metadata)} chunks from {rag_dir}{RESET}")
    return metadata

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0.0:
        return -1.0
    return float(np.dot(a, b) / denom)

def retrieve_relevant_chunks(
    query_embedding: np.ndarray,
    metadata,
    *,
    top_k: int,
    min_sim: float,
):
    scored = []

    for idx, chunk in enumerate(metadata):
        emb = chunk.get("embedding")
        if emb is not None:
            sim = cosine_similarity(query_embedding, emb)
            scored.append((sim, idx, chunk))

    # Sort by descending similarity, then by index
    scored.sort(key=lambda x: (-x[0], x[1]))

    # Keep only chunks above min_sim
    filtered = [chunk for sim, _, chunk in scored if sim >= min_sim]

    # Return top_k full chunks
    return filtered[:top_k]

import numpy as np
import ollama

# Create a persistent client once
client = ollama.Client()

def embed_query(text: str, *, embed_model: str) -> np.ndarray:
    """
    Return the embedding for `text` using Ollama's Python API.
    """
    response = client.embeddings(
        model=embed_model,
        prompt=text
    )
    # Ollama API returns embedding as a list
    return np.array(response["embedding"], dtype=np.float64)


def build_rag_context(
    user_prompt: str,
    *,
    metadata,
    embed_model: str,
    top_k: int,
    min_sim: float,
) -> str:

    # --------------------------------------------------
    # Embed the user prompt
    # --------------------------------------------------
    q = embed_query(
        user_prompt,
        embed_model=embed_model,
    )

    # --------------------------------------------------
    # Retrieve most relevant chunks (FULL chunk dicts)
    # --------------------------------------------------
    chunks = retrieve_relevant_chunks(
        q,
        metadata,
        top_k=top_k,
        min_sim=min_sim,
    )

    # --------------------------------------------------
    # Reconstruct rich context for LLM (metadata + code)
    # --------------------------------------------------
    contexts = []
    output_file = "retrieved_rag_chunks_for_the_user_prompt.txt"

    with open(output_file, "w") as f:
        for i, chunk in enumerate(chunks, 1):
            code = chunk.get("text", "")

            enriched = f"""
            {code}
            """
            f.write(enriched)
            contexts.append(enriched)

    print(f"[INFO] Retrieved RAG chunks saved to {output_file}")

    # --------------------------------------------------
    # Return combined context for the LLM
    # --------------------------------------------------
    return "\n\n".join(contexts)

