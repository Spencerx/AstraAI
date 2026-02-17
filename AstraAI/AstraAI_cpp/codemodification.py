# rag.py
import json
import os
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from rag import build_rag_context
import re
import sys
from regex import extract_class_name
from regex import extract_file_name
from ast_cpp import extract_member_variables

def classify_task_llm(prompt: str, pr, run_llm: Callable) -> str:
    """
    Classify a user prompt into one of the predefined task types
    for code modification in a repo-aware HPC/C++ codebase.

    Arguments:
        prompt: User request string
        pr: Repository / project context object
        run_llm: Callable that takes (prompt, pr) and returns LLM output

    Returns:
        task_type: One of the task keywords or 'LEGACY' if unknown
    """

    # Task types with multiple phrasings for LLM guidance
    task_types = """
ADD_CLASS_METHOD: Add a new function to a class (header + cpp)
ADD_CLASS_METHOD: Implement a function
ADD_CLASS_METHOD: Implement a method
MERGE_CODE_SNIPPET_AS_FUNCTION: Wrap code snippet as a function and merge into a class
CALL_EXISTING_FUNCTION: Insert a call to an existing function
ADD_MEMBER_VARIABLE: Add a member variable to a class
MODIFY_EXISTING_METHOD: Modify the body of an existing method
WIRE_TWO_SUBSYSTEMS: Connect two parts of the code (e.g., solver + advection)
"""

    # Construct LLM prompt
    llm_prompt = f"""
You are a code assistant.

Given a user prompt, classify it into **one** of the following task types:

{task_types}

Return only the task type keyword, nothing else.

User prompt:
"{prompt}"
"""

    # Run LLM
    task_type_raw = run_llm(llm_prompt, pr)

    # Clean and extract only the keyword (ignore explanations or extra text)
    task_type_clean = re.split(r"[:\s]", task_type_raw.strip().upper())[0]

    # Build valid task type list
    valid_task_types = list(set([
        line.split(":", 1)[0].strip().upper()
        for line in task_types.strip().splitlines()
        if line.strip()
    ]))

    # Final check
    if task_type_clean not in valid_task_types:
        return "LEGACY"

    return task_type_clean
 
def handle_add_class_method(
    *,
    user_prompt: str,
    pr: Optional[int],
    log: Callable,
    run_llm: Callable,
    emit_response: Callable,
    emit_response_code_only: Callable,
    rag_metadata,
    top_k,
    embed_model: str,
    class_name: str,
    file_name: str) -> None:

    """
    Code modification using RAG context + LLM.
    """

    log("[INFO] Handling RAG-based code generation")

    # -----------------------------
    # Retrieve context via RAG
    # -----------------------------
    context = build_rag_context(
        user_prompt,
        metadata=rag_metadata,
        embed_model=embed_model,
        top_k=top_k,
        min_sim=0.3,
    )

    #print(context)

    members = extract_member_variables(
        class_name,
        file_name,
        compile_commands_path="compile_commands.json"
    )

    member_context = "\n".join(members)

    # -----------------------------
    # Build code advising prompt
    # -----------------------------
    prompt = f"""
You are an AMReX / C++ expert. Your task is to write correct, compilable C++ code.

Write the requested C++ function below:
USER PROMPT:
{user_prompt}

CONSTRAINTS (STRICT):
1. Do NOT modify the function signature.
2. Do NOT add arguments.
3. All required data already exists as class members.
4. Access class members directly.
5. Do NOT redefine any member variables.
6. Write exactly one function definition.
7. Output ONLY the function code.
8. Use MFIter and ParallelFor for GPU parallelization.


---------------- REFERENCE CONTEXT ----------------
{context}   

CLASS MEMBER VARIABLES:
{member_context}

------------------------------------------------
Output only valid C++ code. Do not use Python, pseudocode, or any other language.
Use proper C++ types, loops, and AMReX constructs.
"""
    print(prompt)


    # -----------------------------
    # LLM call
    # -----------------------------
    response = run_llm(prompt, pr)
    if not response:
        return

    emit_response_code_only(
        pr,
        response,
    )

    sys.exit()


def handle_legacy_llm_rag(*,
    user_prompt: str,
    pr: Optional[int],
    log: Callable,
    run_llm: Callable,
    emit_response: Callable,
    rag_metadata,
    top_k,
    embed_model: str,
    ) -> None:


    """
    Code modification using RAG context + LLM.
    """

    log("[INFO] Handling RAG-based code generation")

    # -----------------------------
    # Retrieve context via RAG
    # -----------------------------
    context = build_rag_context(
        user_prompt,
        metadata=rag_metadata,
        embed_model=embed_model,
        top_k=top_k,
        min_sim=0.3,
    )

    print(context)    


    sys.exit()
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

def handle_codemodification(*,
    user_prompt: str,
    pr: Optional[int],
    log: Callable,
    run_llm: Callable,
    emit_response: Callable,
    emit_response_code_only: Callable,
    rag_metadata,
    top_k,
    embed_model: str,
    ):

    task_type = classify_task_llm(prompt=user_prompt,
                                      pr=pr,
                                      run_llm=run_llm)

    print("The task type is", task_type)

    if(task_type == "ADD_CLASS_METHOD"):
       #find the class into which the function has to be addedi
        class_name = extract_class_name(prompt=user_prompt);
        file_name = extract_file_name(prompt=user_prompt);
        print("The class name is ", class_name);
        print("The file name is ", file_name);
        if(class_name == None):
            print("You are trying to do file modification by adding a function to a class. "
                   "This requires specifying the name of the class into which the change has to be made")
            sys.exit();

    log(f"[INFO] task_type = {task_type}")

    if task_type == "ADD_CLASS_METHOD":
        handle_add_class_method(user_prompt=user_prompt,
                                pr=pr,
                                log=log,
                                run_llm=run_llm,
                                emit_response=emit_response,
                                emit_response_code_only=emit_response_code_only,
                                rag_metadata=rag_metadata,
                                top_k=top_k,
                                embed_model=embed_model,
                                class_name=class_name,
                                file_name=file_name,
                                )
