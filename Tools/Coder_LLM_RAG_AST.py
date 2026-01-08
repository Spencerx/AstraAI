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
parser = argparse.ArgumentParser(description="RAG-based code scaffolding with Ollama")
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

    scored.sort(key=lambda x: (-x[0], x[1]))
    filtered = [text for sim, _, text in scored if sim >= min_sim]
    return filtered[:top_k]

# -------------------------------
# Ollama helpers
# -------------------------------
def run_ollama(prompt, model):
    env = os.environ.copy()
    env["OLLAMA_TEMPERATURE"] = "0"
    env["OLLAMA_TOP_P"] = "1"
    env["OLLAMA_TOP_K"] = "1"

    try:
        proc = subprocess.run(
            [OLLAMA_BIN, "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        return proc.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Ollama failed:\n{e.stderr or e.stdout}")
        return None

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
# Intent extraction (filename)
# -------------------------------
def extract_intent(query):
    prompt = f"""
Extract the target output file from the user request.

Rules:
- Return JSON only.
- Include a "filename" field.
- If the user did not specify a filename, infer a reasonable one.
- Do not include explanations.

User request:
{query}
"""
    out = run_ollama(prompt, MODEL_NAME)
    if out is None:
        return None

    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print("[ERROR] Failed to parse intent JSON:")
        print(out)
        return None

# -------------------------------
# Interactive loop
# -------------------------------
print("RAG-based code scaffolding")
print("Type 'exit' to quit.\n")

while True:
    query = input("Enter your request: ").strip()
    if query.lower() == "exit":
        break
    if not query:
        print("Please enter a non-empty request.")
        continue

    intent = extract_intent(query)
    if intent is None or "filename" not in intent:
        print("[ERROR] Could not determine output filename.")
        continue

    filename = intent["filename"]
    print(f"Target file: {filename}")

    canonical_query = f"AMReX C++ code generation request: {query}"
    query_embedding = get_embedding(canonical_query)
    if query_embedding is None:
        print("Failed to generate embedding.")
        continue

    relevant_chunks = retrieve_relevant_chunks(query_embedding, metadata)
    context = "\n\n".join(relevant_chunks)

    prompt = f"""
You are an AMReX expert C++ developer.

Using the context below as reference examples and patterns,
generate a complete, compilable source file.

Rules:
- You MAY synthesize new code.
- Follow AMReX best practices shown in the context.
- Output ONLY valid source code.
- Do NOT include markdown, explanations, or extra text.
- The file will be saved as: {filename}

Context:
{context}

User request:
{query}
"""

    code = run_ollama(prompt, MODEL_NAME)
    if code is None:
        print("Code generation failed.")
        continue

    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    with open(filename, "w") as f:
        f.write(code)

    print(f"[OK] Wrote file: {filename}\n")

