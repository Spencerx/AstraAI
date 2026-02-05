#!/usr/bin/env python3

import os
import json
import uuid
import argparse
import time
import requests
from pathlib import Path

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
VALID_EXTENSIONS = {".cpp", ".cc", ".H", ".h", ".f90", ".F90"}
VALID_FILENAMES = {"inputs"}
EXCLUDE_DIRS = {".git", "build", "CMakeFiles"}

OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"

MAX_EMBED_CHARS = 3000        # HARD safety limit
CODE_EMBED_LINES = 80
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


# ------------------------------------------------------------
# Fortran metadata extractor
# ------------------------------------------------------------
def extract_chunks(file_path, example_name, example_root):
    chunks = []

    try:
        lines = file_path.read_text().splitlines()
    except Exception as e:
        print(f"[WARN] Skipping {file_path}: {e}")
        return chunks

    # Find all indices where a line starts with "! PURPOSE:"
    purpose_indices = [i for i, line in enumerate(lines) if line.strip().lower().startswith("! purpose:")]

    for idx, start_i in enumerate(purpose_indices):
        # End index is next purpose line or end of file
        end_i = purpose_indices[idx + 1] if idx + 1 < len(purpose_indices) else len(lines)

        block_lines = lines[start_i:end_i]

        # Parse metadata
        purpose_lines = []
        keywords = []
        context_lines = []
        code_lines = []

        i = 0
        n = len(block_lines)

        # First line contains PURPOSE
        first_line = block_lines[0].strip()
        purpose_lines.append(first_line.split(":", 1)[1].strip())
        i += 1

        # Parse metadata lines (! KEYWORDS, ! CONTEXT, or continuation !)
        while i < n:
            line = block_lines[i].strip()
            line_low = line.lower()

            if line_low.startswith("! keywords:"):
                kws = line.split(":", 1)[1]
                keywords.extend([k.strip() for k in kws.split(",") if k.strip()])

            elif line_low.startswith("! context:"):
                context_lines.append(line.split(":", 1)[1].strip())

            elif line.startswith("!"):
                txt = line[1:].strip()
                if context_lines:
                    context_lines.append(txt)
                else:
                    purpose_lines.append(txt)
            else:
                break

            i += 1

        # Collect code lines until ! END CODE CHUNK marker
        for j in range(i, n):
            line = block_lines[j].strip()
            if line.lower() == "! end code chunk":
                break
            code_lines.append(block_lines[j])

        # Try to find a module procedure name (if any)
        proc_name = None
        for line in code_lines:
            if "module procedure" in line.lower():
                tokens = line.replace("&", "").split()
                proc_name = tokens[-1]
                break

        full_code = "\n".join(code_lines)
        code_for_embedding = "\n".join(code_lines[:CODE_EMBED_LINES])

        try:
            rel_path = str(file_path.relative_to(example_root))
        except ValueError:
            rel_path = file_path.name

        # Prepare embedding text safely
        code_snippet = code_for_embedding
        embedding_text = (
            f"PURPOSE:\n{' '.join(purpose_lines)}\n\n"
            f"KEYWORDS:\n{', '.join(keywords)}\n\n"
            f"CONTEXT:\n{' '.join(context_lines)}\n\n"
            "CODE:\n" + code_snippet
        )

        chunks.append({
            "id": str(uuid.uuid4()),
            "text": full_code,
            "metadata": {
                "example": example_name,
                "procedure": proc_name,
                "purpose": " ".join(purpose_lines),
                "keywords": keywords,
                "context": " ".join(context_lines),
                "source_file": file_path.name,
                "relative_path": rel_path,
                "language": "fortran"
            },
            "embedding_text": embedding_text,
            "code_lines": code_lines  # Keep full code lines for debugging if needed
        })

    return chunks


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Extract Fortran RAG metadata with embeddings"
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
