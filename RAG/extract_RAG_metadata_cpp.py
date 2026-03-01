import os
import json
import uuid
import argparse
import textwrap
import time
import requests
from pathlib import Path

VALID_EXTENSIONS = {".cpp", ".cc", ".H", ".h", ".f90", ".F90"}
VALID_FILENAMES = {"inputs"}
EXCLUDE_DIRS = {".git", "build", "CMakeFiles"}

OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embeddings"

MAX_EMBED_CHARS = 3000
CODE_SNIPPET_CHARS = 400   # how much code goes into embedding
EMBED_RETRIES = 2
RETRY_SLEEP = 1.0


# ------------------------------------------------------------
# Ollama embedding
# ------------------------------------------------------------
def embed_text(text: str, model: str):
    text = text.strip()
    if len(text) > MAX_EMBED_CHARS:
        text = text[:MAX_EMBED_CHARS]

    payload = {"model": model, "prompt": text}

    for attempt in range(EMBED_RETRIES):
        try:
            r = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=60)
            if r.status_code == 200:
                return r.json()["embedding"]
            else:
                raise RuntimeError(r.text)
        except Exception as e:
            if attempt + 1 == EMBED_RETRIES:
                raise RuntimeError(f"Ollama embedding failed: {e}")
            time.sleep(RETRY_SLEEP)


# ------------------------------------------------------------
# Parse AI_METADATA block
# ------------------------------------------------------------
def parse_metadata_block(lines, start_idx):
    metadata = {}
    user_intent_lines = []

    i = start_idx + 1
    in_user_intent = False

    while i < len(lines):
        raw = lines[i].strip()

        if not raw.startswith("//"):
            break

        content = raw.lstrip("/").strip()

        # Detect user_intent block
        if content.startswith("user_intent:"):
            in_user_intent = True
            i += 1
            continue

        if in_user_intent:
            if ":" in content:  # next metadata field begins
                in_user_intent = False
            else:
                user_intent_lines.append(content)
                i += 1
                continue

        # Normal key: value pairs
        if ":" in content:
            key, val = content.split(":", 1)
            metadata[key.strip()] = val.strip()

        i += 1

    metadata["user_intent"] = "\n".join(user_intent_lines).strip()
    return metadata, i


# ------------------------------------------------------------
# Extract chunks using AI_METADATA
# ------------------------------------------------------------
def extract_chunks(file_path, example_name, example_root):
    chunks = []

    try:
        lines = file_path.read_text().splitlines()
    except Exception as e:
        print(f"[WARN] Skipping {file_path}: {e}")
        return chunks

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("// AI_METADATA"):
            metadata, i = parse_metadata_block(lines, i)

            code_lines = []
            while i < len(lines):
                if lines[i].strip().startswith("// AI_METADATA"):
                    break
                code_lines.append(lines[i])
                i += 1

            full_code = textwrap.dedent("\n".join(code_lines))

            try:
                rel_path = str(file_path.relative_to(example_root))
            except ValueError:
                rel_path = file_path.name

            # 🔴 NEW: embedding uses ONLY user_intent + code
            embedding_text = (
                f"USER INTENT:\n{metadata.get('user_intent','')}\n\n"
                #f"CODE SNIPPET:\n{full_code[:CODE_SNIPPET_CHARS]}"
            )

            chunks.append({
                "id": str(uuid.uuid4()),
                "text": full_code,
                "metadata": {
                    "example": example_name,
                    "source_file": file_path.name,
                    "relative_path": rel_path,
                    "language": file_path.suffix,
                    **metadata
                },
                "embedding_text": embedding_text
            })
        else:
            i += 1

    return chunks


# ------------------------------------------------------------
# Process one code directory → one json
# ------------------------------------------------------------
def process_codebase(code_dir, out_dir, embed_model):
    example_name = code_dir.name
    output_file = out_dir / f"{example_name}.json"

    print(f"\n[INFO] Processing codebase: {example_name}")

    all_chunks = []

    for path in code_dir.rglob("*"):
        if any(p in EXCLUDE_DIRS for p in path.parts):
            continue
        if path.suffix not in VALID_EXTENSIONS and path.name not in VALID_FILENAMES:
            continue

        all_chunks.extend(extract_chunks(path, example_name, code_dir))

    print(f"[INFO] Found {len(all_chunks)} AI_METADATA chunks")

    embedded = 0
    for chunk in all_chunks:
        try:
            chunk["embedding"] = embed_text(
                chunk.pop("embedding_text"),
                embed_model
            )
            embedded += 1
        except Exception as e:
            print(f"[WARN] Embedding failed: {e}")
            chunk["embedding"] = None

    metadata = {
        "example": example_name,
        "num_chunks": embedded,
        "chunks": all_chunks
    }

    with open(output_file, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[OK] Wrote → {output_file}")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Extract AI_METADATA chunks with embeddings (user_intent focused)"
    )
    parser.add_argument("--code-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--embed-model", required=True)

    args = parser.parse_args()

    code_root = Path(args.code_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for subdir in code_root.iterdir():
        if subdir.is_dir():
            process_codebase(subdir, out_dir, args.embed_model)


if __name__ == "__main__":
    main()

