#!/usr/bin/env python3
import json
import numpy as np
import subprocess
import argparse
import os
import sys
import re

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
parser.add_argument("--hpc-code-examples-dir", type=str, required=False,  
                    default=None, help="Directory containing code examples (optional)")
parser.add_argument("--top-k", type=int, default=3,
                    help="Number of chunks to retrieve")
parser.add_argument("--min-sim", type=float, default=0.45,
                    help="Minimum cosine similarity threshold")
parser.add_argument("--ollama-bin", type=str, default="ollama",
                    help="Path to the Ollama executable")
parser.add_argument("--prompt-file", type=str, required=True,
                    help="File containing the full user prompt")
args = parser.parse_args()

MODEL_NAME = args.llm_model
EMBED_MODEL = args.embed_model
RAG_DIR = args.rag_dir
TOP_K = args.top_k
MIN_SIM = args.min_sim
OLLAMA_BIN = args.ollama_bin
PROMPT_FILE = args.prompt_file

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

    # Deterministic ordering: similarity DESC, index ASC
    scored.sort(key=lambda x: (-x[0], x[1]))
    filtered = [text for sim, _, text in scored if sim >= min_sim]
    return filtered[:top_k]

# -------------------------------
# Ollama helpers (Python 3.6 compatible)
# -------------------------------
def run_ollama(prompt, model):
    env = os.environ.copy()
    env["OLLAMA_TEMPERATURE"] = "0"
    env["OLLAMA_TOP_P"] = "1"
    env["OLLAMA_TOP_K"] = "1"
    env["OLLAMA_LOG"] = "0"  # suppress Ollama logging

    proc = subprocess.Popen(
        [OLLAMA_BIN, "run", model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        universal_newlines=True
    )
    stdout, stderr = proc.communicate(input=prompt)
    if proc.returncode != 0:
        print(f"[ERROR] Ollama failed:\n{stderr.strip() or stdout.strip()}")
        return None
    return stdout.strip()

def get_embedding(text):
    if not text.strip():
        return None
    proc = subprocess.Popen(
        [OLLAMA_BIN, "run", EMBED_MODEL],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, stderr = proc.communicate(input=text)
    if proc.returncode != 0:
        print(f"[ERROR] Ollama embedding failed:\n{stderr.strip() or stdout.strip()}")
        return None
    try:
        return np.array(json.loads(stdout.strip()), dtype=np.float64)
    except Exception as e:
        print(f"[ERROR] Failed to parse embedding: {e}")
        return None

# -------------------------------
# Read full prompt from file
# -------------------------------
if not os.path.exists(PROMPT_FILE):
    print(f"[ERROR] Prompt file {PROMPT_FILE} not found")
    sys.exit(1)

with open(PROMPT_FILE, "r") as f:
    user_prompt = f.read().strip()

if not user_prompt:
    print("[ERROR] Prompt file is empty")
    sys.exit(1)

# -------------------------------
# Determine output file from prompt
# -------------------------------
match = re.search(r'(\S+\.(?:cpp|cxx|cc|h|H|hpp))', user_prompt, re.IGNORECASE)
if match:
    OUTPUT_FILE = match.group(1)
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    print(f"Target file: {OUTPUT_FILE}")
else:
    print("[ERROR] Could not determine output filename from prompt. Include filename (e.g., src/main.cpp) in request.")
    sys.exit(1)

# -------------------------------
# Generate code via RAG + LLM
# -------------------------------
canonical_query = f"AMReX C++ code generation request: {user_prompt}"
query_embedding = get_embedding(canonical_query)
if query_embedding is None:
    print("[ERROR] Failed to generate embedding")
    sys.exit(1)

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
Rules (must follow):
- Output ONLY valid C++ source code.
- Output MUST begin with a valid C++ token (#include, int, using, namespace).
- Output MUST NOT include markdown, backticks, explanations, or extra text.
- DO NOT include phrases like "Here is", "Below is", or "This file".
- The output MUST contain exactly the code that should go in the file.
- The file can be a .cpp or .h file depending on the user request.


Context:
{context}

User request:
{user_prompt}
"""

code = run_ollama(prompt, MODEL_NAME)
if code is None:
    print("[ERROR] Code generation failed")
    sys.exit(1)

# -------------------------------
# Write code to file
# -------------------------------
with open(OUTPUT_FILE, "w") as f:
    f.write(code)

print(f"[OK] Wrote file: {OUTPUT_FILE}")
