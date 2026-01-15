import argparse
import sys
import os

# Add the parent directory of this file to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from llm import run_ollama
from embeddings import get_embedding
from rag import load_rag_metadata, retrieve_relevant_chunks
from prompt_io import read_user_prompt, resolve_output_file
from scaffold_state import scaffold_exists, write_scaffold_state

def main():
    parser = argparse.ArgumentParser(
        description="RAG-based code scaffolding with Ollama"
    )
    parser.add_argument("--llm-model", required=True)
    parser.add_argument("--embed-model", required=True)
    parser.add_argument("--rag-dir", required=True)
    parser.add_argument("--hpc-code-examples-dir", default=None)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-sim", type=float, default=0.45)
    parser.add_argument("--ollama-bin", default="ollama")
    parser.add_argument("--prompt-file", required=True)

    args = parser.parse_args()

    user_prompt = read_user_prompt(args.prompt_file)

    from intent import get_user_intent
    from scaffold import copy_scaffold
    import os, sys

    intent = get_user_intent(user_prompt, args.llm_model, args.ollama_bin)

    print("The intent is ", intent);
    
    if intent == "scaffolding":

        if scaffold_exists():
            print("[INFO] AMReX scaffold already exists. Skipping scaffolding.")
            sys.exit(0)

        if not args.hpc_code_examples_dir:
            print("[ERROR] --hpc-code-examples-dir is required for scaffolding")
            sys.exit(1)

        target_dir = "src"
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        copy_scaffold(args.hpc_code_examples_dir, target_dir)

        write_scaffold_state(
            scaffold_type=os.path.basename(args.hpc_code_examples_dir),
            intent=intent,
            user_prompt=user_prompt
        )

        print("[OK] AMReX scaffold created.")
        sys.exit(0)

    output_file = resolve_output_file(user_prompt)

    metadata = load_rag_metadata(args.rag_dir)

    canonical_query = f"AMReX C++ code generation request: {user_prompt}"
    query_embedding = get_embedding(
        canonical_query, args.embed_model, args.ollama_bin
    )

    if query_embedding is None:
        print("[ERROR] Failed to generate embedding")
        sys.exit(1)

    chunks = retrieve_relevant_chunks(
        query_embedding, metadata, args.top_k, args.min_sim
    )

    context = "\n\n".join(chunks)

    prompt = f"""
You are an AMReX expert C++ developer.

Using the context below as reference examples and patterns,
generate a complete, compilable source file.

Rules:
- Output ONLY valid C++ source code.
- Output MUST begin with a valid C++ token.
- Do NOT include markdown or explanations.

Context:
{context}

User request:
{user_prompt}
"""

    code = run_ollama(prompt, args.llm_model, args.ollama_bin)
    if code is None:
        print("[ERROR] Code generation failed")
        sys.exit(1)

    with open(output_file, "w") as f:
        f.write(code)

    print(f"[OK] Wrote file: {output_file}")


if __name__ == "__main__":
    main()

