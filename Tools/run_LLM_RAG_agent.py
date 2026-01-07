#!/usr/bin/env python3
import json
import numpy as np
import subprocess
import argparse
import os
import sys
import tempfile
import shutil

# ============================================================
# ARGUMENTS
# ============================================================
parser = argparse.ArgumentParser(description="RAG → aider (locked, non-destructive)")
parser.add_argument("--llm-model", required=True, help="Ollama LLM model")
parser.add_argument("--embed-model", required=True, help="Ollama embedding model")
parser.add_argument("--rag-dir", required=True, help="Directory with RAG JSON")
parser.add_argument("--top-k", type=int, default=3)
parser.add_argument("--ollama-bin", default="ollama", help="Path to Ollama executable")

# HARD LIMITS
parser.add_argument("--files", nargs="+", required=True,
                    help="Explicit list of files aider is allowed to touch")
parser.add_argument("--max-diff-lines", type=int, default=50,
                    help="Abort if aider modifies more than this many lines")

args = parser.parse_args()

MODEL_NAME   = args.llm_model
EMBED_MODEL  = args.embed_model
RAG_DIR      = args.rag_dir
TOP_K        = args.top_k
OLLAMA_BIN   = args.ollama_bin
ALLOWED_FILES = args.files
MAX_DIFF_LINES = args.max_diff_lines

# ============================================================
# AIDER MODEL
# ============================================================
AIDER_MODEL = f"openai/{MODEL_NAME}"
print(f"[INFO] Using aider model: {AIDER_MODEL}")

# Disable aider reflection loop
os.environ["AIDER_REFLECTIONS"] = "0"

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

for c in metadata:
    emb = c.get("embedding")
    if emb is not None:
        c["embedding"] = np.array(json.loads(emb) if isinstance(emb, str) else emb)

# ============================================================
# RAG UTILITIES
# ============================================================
def cosine_similarity(a, b):
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
    p = subprocess.run(
        [OLLAMA_BIN, "run", EMBED_MODEL],
        input=text,
        text=True,
        capture_output=True,
        check=True
    )
    return np.array(json.loads(p.stdout.strip()))

# ============================================================
# AIDER PROMPT (HARD-LOCKED)
# ============================================================
def write_aider_prompt(user_query, context_chunks, path):
    context = "\n\n".join(context_chunks)

    prompt = f"""
CRITICAL RULES (MUST FOLLOW):

- You may ONLY modify the explicitly allowed files
- You MUST use a unified diff
- You may NOT delete files
- You may NOT replace entire files
- You may NOT restate filenames as file content
- You may NOT fix errors or debug
- You may NOT refactor or reformat
- AMReX GPU lambdas, ParallelFor, and macros are correct — do NOT rewrite them
- If no change is required, output an EMPTY diff

CONTEXT (authoritative):
{context}

TASK:
{user_query}

Apply the smallest possible change.
"""
    with open(path, "w") as f:
        f.write(prompt.strip() + "\n")

# ============================================================
# DIFF SAFETY CHECK
# ============================================================
def validate_diff(diff_text):
    added = sum(1 for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_text.splitlines() if l.startswith("-") and not l.startswith("---"))

    if added + removed > MAX_DIFF_LINES:
        raise RuntimeError(f"Diff too large ({added+removed} lines)")

    if "+++ /dev/null" in diff_text or "--- /dev/null" in diff_text:
        raise RuntimeError("File deletion detected")

# ============================================================
# RUN AIDER (SINGLE-SHOT)
# ============================================================
def run_aider(prompt_path):
    with tempfile.TemporaryDirectory() as tmp:
        diff_path = os.path.join(tmp, "changes.diff")

        cmd = [
            "aider",
            "--model", AIDER_MODEL,
            "--edit-format", "diff",
            "--apply",
            "--no-auto-commits",
            "--no-summarize",
            "--no-suggest-shell-commands",
            "--message-file", prompt_path,
            "--diff"
        ]

        for f in ALLOWED_FILES:
            cmd += ["--files", f]

        print("[INFO] Running locked aider...")
        p = subprocess.run(cmd, capture_output=True, text=True)

        diff = p.stdout.strip()
        if not diff:
            print("[INFO] No changes produced.")
            return

        validate_diff(diff)

        print("[INFO] Changes applied safely.")

# ============================================================
# INTERACTIVE LOOP
# ============================================================
print("RAG → locked aider. Type 'exit' to quit.\n")

while True:
    query = input("User task> ").strip()
    if query.lower() == "exit":
        sys.exit(0)

    query_emb = get_embedding(query)
    chunks = retrieve(query_emb)

    if not chunks:
        print("[WARN] No relevant RAG context.")
        continue

    prompt_file = "aider_prompt.txt"
    write_aider_prompt(query, chunks, prompt_file)

    try:
        run_aider(prompt_file)
    except Exception as e:
        print(f"[ABORTED] {e}")
