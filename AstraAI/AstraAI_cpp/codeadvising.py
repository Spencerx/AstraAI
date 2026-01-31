# rag.py
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

    print(f"[RAG] Loaded {len(metadata)} chunks from {rag_dir}")
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

def embed_query(
    text: str,
    *,
    embed_model: str,
    ollama_bin: str,
) -> np.ndarray:

    import subprocess
    import json

    proc = subprocess.Popen(
        [ollama_bin, "run", embed_model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    stdout, stderr = proc.communicate(input=text)

    if proc.returncode != 0:
        raise RuntimeError(stderr.strip() or stdout.strip())

    return np.array(json.loads(stdout.strip()), dtype=np.float64)


def build_rag_context(
    user_prompt: str,
    *,
    metadata,
    embed_model: str,
    ollama_bin: str,
    top_k: int,
    min_sim: float,
) -> str:

    # --------------------------------------------------
    # Embed the user prompt
    # --------------------------------------------------
    q = embed_query(
        user_prompt,
        embed_model=embed_model,
        ollama_bin=ollama_bin,
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
            meta = chunk.get("metadata", {})
            code = chunk.get("text", "")

            enriched = f"""
FUNCTION: {meta.get('function', '')}
FEATURES: {", ".join(meta.get('features', []))}
FILE: {meta.get('source_file', '')}

CODE:
{code}
"""

            f.write(f"--- Chunk {i} ---\n{enriched}\n\n")
            contexts.append(enriched)

    print(f"[INFO] Retrieved RAG chunks saved to {output_file}")

    # --------------------------------------------------
    # Return combined context for the LLM
    # --------------------------------------------------
    return "\n\n".join(contexts)

def handle_codeadvising(
    *,
    user_prompt: str,
    pr: Optional[int],
    log: Callable,
    run_llm: Callable,
    emit_response: Callable,
    rag_metadata,
    top_k,
    embed_model: str,
    ollama_bin: str,
) -> None:
    """
    Code generation using RAG context + LLM.
    """

    log("[INFO] Handling RAG-based code generation")

    # -----------------------------
    # Retrieve context via RAG
    # -----------------------------
    context = build_rag_context(
        user_prompt,
        metadata=rag_metadata,
        embed_model=embed_model,
        ollama_bin=ollama_bin,
        top_k=top_k,
        min_sim=0.3,
    )


    # -----------------------------
    # Build code advising prompt
    # -----------------------------
    prompt = f"""
You are an AMReX expert
Output C++ code

You are given reference code from a large HPC codebase.
This is NOT the answer.
It is background knowledge to help you understand available APIs,
data structures, naming conventions, and style.

Use this knowledge to write new code that satisfies the user request.

Do not copy large portions of the reference unless necessary.
Do not output the reference code itself.

---------------- REFERENCE CODE ----------------
{context}
------------------------------------------------

USER PROMPT:
{user_prompt}
"""
    # -----------------------------
    # LLM call
    # -----------------------------
    response = run_llm(prompt, pr)
    if not response:
        return

    emit_response(
        pr,
        "### 🧠 RAG Code Generation\n\n```cpp\n" + response + "\n```",
    )
