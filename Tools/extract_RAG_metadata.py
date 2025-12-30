#!/usr/bin/env python3

import os
import json
import uuid
import argparse
from pathlib import Path
import textwrap

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
VALID_EXTENSIONS = {".cpp", ".cc", ".H", ".h", ".f90", ".F90"}
VALID_FILENAMES = {"inputs"}  # include files like 'inputs'
EXCLUDE_DIRS = {".git", "build", "CMakeFiles"}

# ------------------------------------------------------------
# Extract chunks from a file
# ------------------------------------------------------------
def extract_chunks(file_path, example_name, example_root):
    """
    Extract chunks from a file.
    Handles:
      - C++ files with multi-line signatures and braces
      - Inputs or other text files with # FUNCTION: / # FEATURES:
      - Everything after FEATURES until next FUNCTION or EOF
    """
    chunks = []

    try:
        lines = file_path.read_text().splitlines()
    except Exception as e:
        print(f"[WARN] Skipping {file_path}: {e}")
        return chunks

    i = 0
    while i < len(lines):
        line = lines[i].lstrip()
        # Match both C++ and shell-style FUNCTION lines
        if line.startswith("// FUNCTION:") or line.startswith("# FUNCTION:"):
            function_desc = line.split(":", 1)[1].strip()

            # FEATURES line (next line)
            features = []
            if i + 1 < len(lines):
                next_line = lines[i + 1].lstrip()
                if next_line.startswith("// FEATURES:") or next_line.startswith("# FEATURES:"):
                    features = [f.strip() for f in next_line.split(":", 1)[1].split(",") if f.strip()]
                    i += 2
                else:
                    i += 1
            else:
                i += 1

            # Collect all lines until next FUNCTION line or EOF
            code_lines = []
            while i < len(lines):
                l = lines[i]
                if l.lstrip().startswith("// FUNCTION:") or l.lstrip().startswith("# FUNCTION:"):
                    break
                code_lines.append(l)
                i += 1

            code_snippet = textwrap.dedent("\n".join(code_lines))

            # Determine language
            language = "cpp" if file_path.suffix in VALID_EXTENSIONS else "txt"

            # Relative path
            try:
                rel_path = str(file_path.relative_to(example_root))
            except ValueError:
                rel_path = file_path.name

            chunk = {
                "id": str(uuid.uuid4()),
                "text": code_snippet,
                "metadata": {
                    "example": example_name,
                    "function": function_desc,
                    "features": features,
                    "source_file": file_path.name,
                    "relative_path": rel_path,
                    "language": language
                }
            }
            chunks.append(chunk)
        else:
            i += 1

    # Fallback: if no FUNCTION lines at all, include full file as one chunk
    if not chunks:
        code_snippet = "\n".join(lines)
        try:
            rel_path = str(file_path.relative_to(example_root))
        except ValueError:
            rel_path = file_path.name

        chunk = {
            "id": str(uuid.uuid4()),
            "text": code_snippet,
            "metadata": {
                "example": example_name,
                "function": "full file",
                "features": ["inputs"] if file_path.name in VALID_FILENAMES else [],
                "source_file": file_path.name,
                "relative_path": rel_path,
                "language": "txt" if file_path.suffix == "" else "cpp"
            }
        }
        chunks.append(chunk)

    return chunks

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Extract portable RAG metadata from annotated AMReX codebase"
    )
    parser.add_argument(
        "--code_dir",
        required=True,
        help="Path to example codebase directory"
    )
    parser.add_argument(
        "--out_dir",
        required=True,
        help="Directory to write metadata JSON"
    )

    args = parser.parse_args()
    code_dir = Path(args.code_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not code_dir.is_dir():
        raise RuntimeError(f"code_dir does not exist: {code_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    example_name = code_dir.name
    output_file = out_dir / f"{example_name}.json"

    all_chunks = []

    for path in code_dir.rglob("*"):
        if any(p in EXCLUDE_DIRS for p in path.parts):
            continue
        if path.suffix not in VALID_EXTENSIONS and path.name not in VALID_FILENAMES:
            continue

        chunks = extract_chunks(path, example_name, code_dir)
        all_chunks.extend(chunks)

    metadata = {
        "example": example_name,
        "num_chunks": len(all_chunks),
        "chunks": all_chunks
    }

    with open(output_file, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[OK] Wrote {len(all_chunks)} chunks → {output_file}")


if __name__ == "__main__":
    main()


