#!/usr/bin/env python3

import os
import json
import uuid
import argparse
import textwrap
import time
import requests
from pathlib import Path
import sys

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
VALID_EXTENSIONS = {".cpp", ".cc", ".H", ".h", ".f90", ".F90"}
VALID_FILENAMES = {"inputs"}
EXCLUDE_DIRS = {".git", "build", "CMakeFiles"}

OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"

MAX_EMBED_CHARS = 3000        # HARD safety limit
CODE_EMBED_LINES = 80        # AMReX-friendly
EMBED_RETRIES = 2
RETRY_SLEEP = 1.0

# ------------------------------------------------------------
# Ollama embedding
# ------------------------------------------------------------
def embed_text(text: str, model: str):
    text = text.strip()
    if len(text) > MAX_EMBED_CHARS:
        text = text[:MAX_EMBED_CHARS]

    payload = {
        "model": model,
        "prompt": text
    }

    for attempt in range(EMBED_RETRIES):
        try:
            r = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=60)
            if r.status_code == 200:
                return r.json()["embedding"]
            else:
                raise RuntimeError(r.text)
        except Exception as e:
            if attempt + 1 == EMBED_RETRIES:
                raise RuntimeError(f"Ollama embedding failed after retries: {e}")
            time.sleep(RETRY_SLEEP)

def extract_chunks(file_path, example_name, example_root):
    chunks = []

    try:
        lines = file_path.read_text().splitlines()
    except Exception as e:
        print(f"[WARN] Skipping {file_path}: {e}")
        return chunks

    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        # --------------------------------------------------
        # Detect metadata start
        # --------------------------------------------------
        if line.startswith("! PURPOSE:"):

            purpose_lines = [line.split(":", 1)[1].strip()]
            keywords = []
            context_lines = []

            i += 1

            # ---------------- Parse metadata block ----------------
            while i < n:
                cur = lines[i].strip()

                if cur.startswith("! KEYWORDS:"):
                    kws = cur.split(":", 1)[1]
                    keywords.extend([k.strip() for k in kws.split(",") if k.strip()])

                elif cur.startswith("! CONTEXT:"):
                    context_lines.append(cur.split(":", 1)[1].strip())

                elif cur.startswith("!"):
                    txt = cur[1:].strip()
                    if context_lines:
                        context_lines.append(txt)
                    else:
                        purpose_lines.append(txt)
                else:
                    break

                i += 1

            purpose = " ".join(purpose_lines)
            context = " ".join(context_lines)

            # ---------------- Find module procedure safely ----------------
            proc_name = None
            search_i = i
            while search_i < n:
                s = lines[search_i].strip().lower()

                if s.startswith("! purpose:"):
                    break  # next block, abort

                if "module procedure" in s:
                    proc_name = lines[search_i].strip().split()[-1]
                    break

                search_i += 1

            if not proc_name:
                i = search_i
                continue

            # Move i to line after module procedure
            i = search_i + 1

            # ---------------- Collect code ----------------
            code_lines = []
            while i < n:
                s = lines[i].strip().lower()

                # Stop only if a NEW metadata block begins
                if s.startswith("! purpose:"):
                    break

                code_lines.append(lines[i])
                i += 1

            full_code = "\n".join(code_lines)
            code_for_embedding = "\n".join(code_lines[:40])

            try:
                rel_path = str(file_path.relative_to(example_root))
            except ValueError:
                rel_path = file_path.name

            chunks.append({
                "id": str(uuid.uuid4()),
                "text": full_code,
                "metadata": {
                    "example": example_name,
                    "procedure": proc_name,
                    "purpose": purpose,
                    "keywords": keywords,
                    "context": context,
                    "source_file": file_path.name,
                    "relative_path": rel_path,
                    "language": "fortran"
                },
                "embedding_text": (
                    f"PURPOSE:\n{purpose}\n\n"
                    f"KEYWORDS:\n{', '.join(keywords)}\n\n"
                    f"CONTEXT:\n{context}\n\n"
                    f"CODE:\n{code_for_embedding}"
                )
            })

        else:
            i += 1

    return chunks

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Extract AMReX RAG metadata with embeddings"
    )
    parser.add_argument("--code-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--embed-model", required=True)

    args = parser.parse_args()

    code_dir = Path(args.code_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    example_name = code_dir.name
    output_file = out_dir / f"{example_name}.json"

    all_chunks = []

    for path in code_dir.rglob("*"):
        if any(p in EXCLUDE_DIRS for p in path.parts):
            continue
        if path.suffix not in VALID_EXTENSIONS and path.name not in VALID_FILENAMES:
            continue

        all_chunks.extend(extract_chunks(path, example_name, code_dir))

    print(f"[INFO] Embedding {len(all_chunks)} chunks using {args.embed_model}")

    embedded = 0
    for chunk in all_chunks:
        try:
            chunk["embedding"] = embed_text(
                chunk.pop("embedding_text"),
                args.embed_model
            )
            embedded += 1
        except Exception as e:
            print(f"[WARN] Skipping chunk {chunk['id']}: {e}")
            chunk["embedding"] = None

    metadata = {
        "example": example_name,
        "num_chunks": embedded,
        "chunks": all_chunks
    }

    with open(output_file, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[OK] Wrote {embedded} embeddings → {output_file}")

if __name__ == "__main__":
    main()
