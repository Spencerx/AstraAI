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
    while i < len(lines):
        line = lines[i].lstrip()

        # --------------------------------------------------
        # Detect FUNCTION header
        # --------------------------------------------------
        if line.startswith("// FUNCTION:") or line.startswith("# FUNCTION:"):

            function_lines = []
            features_lines = []

            # First FUNCTION line
            function_lines.append(line.split(":", 1)[1].strip())
            i += 1

            mode = "function"

            # --------------------------------------------------
            # Consume comment header block
            # --------------------------------------------------
            while i < len(lines):
                cur = lines[i].lstrip()

                # Stop when real code begins
                if not (cur.startswith("//") or cur.startswith("#")):
                    break

                content = cur.lstrip("/#").strip()

                if content.startswith("FEATURES:"):
                    mode = "features"
                    features_lines.append(content.split(":", 1)[1].strip())
                else:
                    if mode == "function":
                        function_lines.append(content)
                    else:
                        features_lines.append(content)

                i += 1

            function_desc = " ".join(function_lines).strip()

            # Parse features
            features = []
            for fl in features_lines:
                for f in fl.split(","):
                    if f.strip():
                        features.append(f.strip())

            # --------------------------------------------------
            # Collect actual code (UNCHANGED LOGIC)
            # --------------------------------------------------
            code_lines = []
            while i < len(lines):
                nxt = lines[i].lstrip()
                if nxt.startswith("// FUNCTION:") or nxt.startswith("# FUNCTION:"):
                    break
                code_lines.append(lines[i])
                i += 1

            full_code = textwrap.dedent("\n".join(code_lines))
            code_for_embedding = "\n".join(code_lines[:CODE_EMBED_LINES])

            try:
                rel_path = str(file_path.relative_to(example_root))
            except ValueError:
                rel_path = file_path.name

            chunks.append({
                "id": str(uuid.uuid4()),
                "text": full_code,
                "metadata": {
                    "example": example_name,
                    "function": function_desc,
                    "features": features,
                    "source_file": file_path.name,
                    "relative_path": rel_path,
                    "language": "cpp" if file_path.suffix else "txt"
                },
                "embedding_text": (
                    f"FUNCTION:\n{function_desc}\n\n"
                    f"FEATURES:\n{', '.join(features)}\n\n"
                    f"CODE:\n{code_lines[:10]}"  # just the first few lines
                )
            })

        else:
            i += 1

    # --------------------------------------------------
    # Fallback: whole file
    # --------------------------------------------------
    if not chunks:
        full_code = "\n".join(lines)
        code_for_embedding = "\n".join(lines[:CODE_EMBED_LINES])

        try:
            rel_path = str(file_path.relative_to(example_root))
        except ValueError:
            rel_path = file_path.name

        chunks.append({
            "id": str(uuid.uuid4()),
            "text": full_code,
            "metadata": {
                "example": example_name,
                "function": "full file",
                "features": [],
                "source_file": file_path.name,
                "relative_path": rel_path,
                "language": "txt"
            },
            "embedding_text": (
                f"FUNCTION:\n{function_desc}\n\n"
                f"FEATURES:\n{', '.join(features)}\n"
            )
        })

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
