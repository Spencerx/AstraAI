#!/usr/bin/env python3
import json
import numpy as np
import subprocess
import argparse
import os
import sys

# -------------------------------
# Command-line arguments
# -------------------------------
parser = argparse.ArgumentParser(description="Deterministic RAG with Ollama")
parser.add_argument("--llm-model", type=str, required=True,
                    help="Name of the Ollama LLM model")
parser.add_argument("--embed-model", type=str, required=True,
                    help="Ollama embedding model")
parser.add_argument("--rag-dir", type=str, required=True,
                    help="Directory containing RAG JSON metadata")
parser.add_argument("--top-k", type=int, default=3,
                    help="Number of chunks to retrieve")
parser.add_argument("--min-sim", type=float, default=0.45,
                    help="Minimum cosine similarity threshold")
parser.add_argument("--ollama-bin", type=str, default="ollama",
                    help="Path to the Ollama executable")
args = parser.parse_args()

MODEL_NAME = args.llm_model
EMBED_MODEL = args.embed_model
RAG_DIR = args.rag_dir
TOP_K = args.top_k
MIN_SIM = args.min_sim
OLLAMA_BIN = args.ollama_bin

# -------------------------------
# Load RAG metadata
# -------------------------------
json_files = sorted(f for f in os.listdir(RAG_DIR) if f.endswith(".json"))
if not json_files:
    raise FileNotFoundError(f"No JSON file found in {RAG_DIR}")

METADATA_FILE = os.path.join(RAG_DIR, json_files[0])
print(f"Using RAG metadata file: {METADATA_FILE}")

with open(METADATA_FILE, "r") as f:
    data = json.load(f)

if isinstance(data, dict) and "chunks" in data:
    metadata = data["chunks"]
elif isinstance(data, list):
    metadata = data
else:
    raise TypeError(f"Unexpected JSON structure: {type(data)}")

# -------------------------------
# Normalize embeddings
# -------------------------------
for chunk in metadata:
    emb = chunk.get("embedding")
    if emb is None:
        chunk["embedding"] = None
    elif isinstance(emb, str):
        chunk["embedding"] = np.array(json.loads(emb), dtype=np.float64)
    else:
        chunk["embedding"] = np.array(emb, dtype=np.float64)

# -------------------------------
# Similarity utilities
# -------------------------------
def cosine_similarity(a, b):
    if a is None or b is None:
        return -1.0
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0.0:
        return -1.0
    return float(np.dot(a, b) / denom)

def retrieve_relevant_chunks(query_embedding, metadata, top_k=TOP_K, min_sim=MIN_SIM):
    scored = []
    for idx, chunk in enumerate(metadata):
        emb = chunk.get("embedding")
        if emb is not None:
            sim = cosine_similarity(query_embedding, emb)
            scored.append((sim, idx, chunk.get("text", "")))

    # Deterministic ordering:
    # 1) similarity DESC
    # 2) chunk index ASC (tie-breaker)
    scored.sort(key=lambda x: (-x[0], x[1]))

    filtered = [text for sim, _, text in scored if sim >= min_sim]
    return filtered[:top_k]

# -------------------------------
# Generate embedding using Ollama
# -------------------------------
def get_embedding(text):
    if not text.strip():
        return None

    try:
        proc = subprocess.run(
            [OLLAMA_BIN, "run", EMBED_MODEL],
            input=text,
            capture_output=True,
            text=True,
            check=True
        )
        return np.array(json.loads(proc.stdout.strip()), dtype=np.float64)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Ollama embedding failed:\n{e.stderr or e.stdout}")
        return None

# -------------------------------
# Ask Ollama (deterministic decoding)
# -------------------------------
def ask_ollama(prompt):
    env = os.environ.copy()
    env["OLLAMA_TEMPERATURE"] = "0"
    env["OLLAMA_TOP_P"] = "1"
    env["OLLAMA_TOP_K"] = "1"

    try:
        proc = subprocess.run(
            [OLLAMA_BIN, "run", MODEL_NAME],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        return proc.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Ollama LLM failed:\n{e.stderr or e.stdout}")
        return "Error generating answer."

# -------------------------------
# Interactive RAG loop
# -------------------------------
print(f"Deterministic RAG")
print(f"  LLM model   : {MODEL_NAME}")
print(f"  Embed model : {EMBED_MODEL}")
print(f"  Top-K       : {TOP_K}")
print(f"  Min sim     : {MIN_SIM}")
print("Type 'exit' to quit.\n")

while True:
    query = input("Enter your question: ").strip()
    if query.lower() == "exit":
        break
    if not query:
        print("Please enter a non-empty question.")
        continue

    # Canonicalize query for stable embeddings
    canonical_query = f"AMReX C++ API question: {query}"

    query_embedding = get_embedding(canonical_query)
    if query_embedding is None:
        print("Failed to generate embedding for query.")
        continue

    relevant_chunks = retrieve_relevant_chunks(query_embedding, metadata)
    context = "\n\n".join(relevant_chunks)

    prompt = f"""
You are an AMReX expert.

Answer the question using ONLY the information in the context below.
If the answer is not present in the context, say:
"Not found in provided context."

Context:
{context}

Question:
{query}

Answer:
"""

    print("\n===== PROMPT BEGIN =====\n")
    print(prompt)
    print("\n===== PROMPT END =====\n")

    answer = ask_ollama(prompt)

    print("\n--- Answer ---\n")
    print(answer)
    print("\n----------------\n")
