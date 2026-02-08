# rag.py
import json
import os
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from rag import build_rag_context


def handle_codeadvising(
    *,
    user_prompt: str,
    pr: Optional[int],
    log: Callable,
    run_llm: Callable,
    emit_response: Callable,
    rag_metadata,
    top_k,
    embed_model: str,
    ollama_bin: str,
) -> None:
    """
    Code generation using RAG context + LLM.
    """

    log("[INFO] Handling RAG-based code generation")

    # -----------------------------
    # Retrieve context via RAG
    # -----------------------------
    context = build_rag_context(
        user_prompt,
        metadata=rag_metadata,
        embed_model=embed_model,
        ollama_bin=ollama_bin,
        top_k=top_k,
        min_sim=0.3,
    )


    # -----------------------------
    # Build code advising prompt
    # -----------------------------
    prompt = f"""
You are an AMReX expert
Output C++ code

You are given reference code from a large HPC codebase.
This is NOT the answer.
It is background knowledge to help you understand available APIs,
data structures, naming conventions, and style.

Use this knowledge to write new code that satisfies the user request.

Do not copy large portions of the reference unless necessary.
Do not output the reference code itself.

---------------- REFERENCE CODE ----------------
{context}
------------------------------------------------

USER PROMPT:
{user_prompt}
"""
    # -----------------------------
    # LLM call
    # -----------------------------
    response = run_llm(prompt, pr)
    if not response:
        return

    emit_response(
        pr,
        "### 🧠 RAG Code Generation\n\n```cpp\n" + response + "\n```",
    )
