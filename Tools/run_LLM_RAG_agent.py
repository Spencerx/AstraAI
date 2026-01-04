#!/usr/bin/env python3
import json
import numpy as np
import subprocess
import argparse
import os
import sys

# ============================================================
# ARGUMENTS
# ============================================================
parser = argparse.ArgumentParser(description="RAG → aider agent (Ollama)")
parser.add_argument("--llm-model", required=True, help="Ollama LLM model")
parser.add_argument("--embed-model", required=True, help="Ollama embedding model")
parser.add_argument("--rag-dir", required=True, help="Directory with RAG JSON")
parser.add_argument("--top-k", type=int, default=3)
parser.add_argument("--ollama-bin", default="ollama", help="Path to Ollama executable")
args = parser.parse_args()

MODEL_NAME   = args.llm_model
EMBED_MODEL  = args.embed_model
RAG_DIR      = args.rag_dir
TOP_K        = args.top_k
OLLAMA_BIN   = args.ollama_bin

# ============================================================
# Use the same LLM for aider
# ============================================================
AIDER_MODEL = f"openai/{MODEL_NAME}"
print(f"[INFO] Using aider model: {AIDER_MODEL}")

# ============================================================
# LOAD RAG METADATA
# ============================================================
json_files = [f for f in os.listdir(RAG_DIR) if f.endswith(".json")]
if not json_files:
    raise FileNotFoundError(f"No JSON file found in {RAG_DIR}")

with open(os.path.join(RAG_DIR, json_files[0])) as f:
    data = json.load(f)

if isinstance(data, dict) and "chunks" in data:
    metadata = data["chunks"]
elif isinstance(data, list):
    metadata = data
else:
    raise TypeError(f"Invalid RAG JSON format: {type(data)}")

# Ensure embeddings are numpy arrays
for c in metadata:
    emb = c.get("embedding")
    if emb is not None:
        if isinstance(emb, str):
            c["embedding"] = np.array(json.loads(emb))
        else:
            c["embedding"] = np.array(emb)

# ============================================================
# RAG UTILITIES
# ============================================================
def cosine_similarity(a, b):
    if a is None or b is None:
        return -1.0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def retrieve(query_emb):
    scored = []
    for c in metadata:
        if c.get("embedding") is not None:
            scored.append((cosine_similarity(query_emb, c["embedding"]),
                           c.get("text", "")))
    scored.sort(reverse=True)
    return [t for _, t in scored[:TOP_K]]

def get_embedding(text):
    try:
        p = subprocess.run(
            [OLLAMA_BIN, "run", EMBED_MODEL],
            input=text,
            text=True,
            capture_output=True,
            check=True
        )
        return np.array(json.loads(p.stdout.strip()))
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Ollama embedding failed: {e.stderr.strip() or e.stdout.strip()}")
        return None

# ============================================================
# AIDER GLUE
# ============================================================
def write_aider_prompt(user_query, context_chunks):
    context = "\n\n".join(context_chunks)
    prompt = f"""
You are an autonomous coding agent with deep AMReX and HPC expertise.

CONTEXT (retrieved, authoritative):
{context}

TASK:
{user_query}

RULES:
- Use ONLY the context above as factual ground truth.
- Modify files ONLY if the task explicitly asks you to.
- Create files ONLY if explicitly requested.
- Keep changes minimal, surgical, and correct.
- If no code change is required, explain why.
- Do NOT delete or modify existing code unless the task explicitly requests it.
- Preserve all existing lines exactly as they are if not instructed otherwise.
- Only add or modify code if necessary to fulfill the task.

OUTPUT:
- Apply changes directly using aider.
"""
    with open("aider_prompt.txt", "w") as f:
        f.write(prompt.strip() + "\n")

def run_aider():
    print(f"[INFO] Running aider with model {AIDER_MODEL}...")
    subprocess.run([
        "aider",
        "--model", AIDER_MODEL,
        "--message-file", "aider_prompt.txt",
        "--yes",
    ], check=True)

# ============================================================
# INTERACTIVE LOOP
# ============================================================
print("RAG → aider agent. Type 'exit' to quit.\n")

while True:
    query = input("User task> ").strip()
    if query.lower() == "exit":
        sys.exit(0)

    query_embedding = get_embedding(query)
    if query_embedding is None:
        print("[ERROR] Failed to generate embedding for query.")
        continue

    chunks = retrieve(query_embedding)
    if not chunks:
        print("[WARN] No relevant chunks retrieved from RAG.")
        continue

    write_aider_prompt(query, chunks)
    run_aider()
