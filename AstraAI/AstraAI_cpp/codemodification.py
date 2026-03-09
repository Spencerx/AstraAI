# rag.py
import json
import os
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from rag import build_rag_context
import re
import sys
from regex import extract_class_name, extract_file_name, extract_function_name
from ast_cpp import extract_member_variables
from ast_cpp import clang_query_span, linecol_to_offset
from code_editing import apply_conflict_patch

def classify_task_llm(prompt: str, pr, run_llm: Callable) -> str:
    return "ADD_CLASS_METHOD"
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
ADD_CLASS_METHOD: Add a new function to a class
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
        return "ADD_CLASS_METHOD"
        #return "LEGACY"

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
    BLUE = "\033[94m"
    RED = "\033[91m"
    RESET = "\033[0m"

    #log("[INFO] Handling RAG-based code generation")

    # -----------------------------
    # Retrieve context via RAG
    # -----------------------------
    print(f"{RED}Performing Retrieval Augmented Generation {RESET}\n")
    context = build_rag_context(
        user_prompt,
        metadata=rag_metadata,
        embed_model=embed_model,
        top_k=top_k,
        min_sim=0.3,
    )

    #print("The context is \n")
    #print(context)
    #sys.exit()



    print(f"{RED}Performing Abstract Syntax Tree info extraction {RESET}\n")
    members = extract_member_variables(
        class_name,
        file_name,
        compile_commands_path="compile_commands.json"
    )

    member_context = "\n".join(members)


    filename = extract_file_name(prompt=user_prompt);
    classname = extract_class_name(prompt=user_prompt);
    funcname = extract_function_name(prompt=user_prompt);

    print("Function name is ", funcname, "\n")

    # get the function span (automatically finds header if free function)
    if(funcname):
        span = clang_query_span(filename, funcname, classname)

        if span is None:
            raise RuntimeError(f"Function {funcname} not found")

        # unpack correctly
        source_file, start_line, start_col, end_line, end_col = span

        # read the file where the function is actually defined
        with open(source_file, "r", encoding="utf-8") as f:
            code = f.read()

        # convert line/col to Python offsets
        start_offset = linecol_to_offset(code, start_line, start_col)
        end_offset   = linecol_to_offset(code, end_line, end_col)
        end_offset = end_offset + 1

        # extract the function text
        original_fn = code[start_offset:end_offset]

        #print("The extracted code function is from file:", source_file)
        #print(original_fn)
        if(original_fn):
            func_code_for_prompt=f"""---------------- THE FUNCTION TO BE MODIFIED -------------
                ```cpp
                {original_fn}
                ```cpp
            """
    else:
        func_code_for_prompt=""
    #print(original_fn);   
    #print()  # spacing before next prompt 



    print(f"{RED}Building the prompt: RAG chunks + AST info + user prompt {RESET}\n")
    # -----------------------------
    # Build code advising prompt
    # -----------------------------
    prompt = f"""
You are an AMReX / C++ expert. Your task is to write correct, compilable C++ code.
Use proper C++ types, loops, and AMReX constructs.

CONSTRAINTS (STRICT):
1. Do NOT modify the function signature.
2. Inlcude ONLY the function and NO header includes.
3. Do NOT add arguments.
4. All required data already exists as class members.
5. Access class members directly.
6. Do NOT redefine any member variables.
7. Use MFIter and ParallelFor for GPU parallelization.
8. Do not add nnecessary variables.

---------------- RAG REFERENCE CONTEXT ----------------
```cpp
{context}   
```

---------------- MEMBER VARIABLE CONTEXT ---------------
The member variables in the class are
```cpp
{member_context}


{func_code_for_prompt}

------------------------------------------------

Write the requested C++ function below:
USER PROMPT:
{user_prompt}

"""
    #print(prompt)
    with open("full_prompt.txt", "w") as f:
        f.write(prompt)

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

    if funcname:
        return {
        "source_file": source_file,
        "code": code,
        "start_offset": start_offset,
        "end_offset": end_offset,
        "generated_function": response,
        }
 
    else:
        return {"generated_function": response,}
    #sys.exit()

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

    #print("The task type is", task_type)

    if(task_type == "ADD_CLASS_METHOD"):
       #find the class into which the function has to be addedi
        class_name = extract_class_name(prompt=user_prompt);
        file_name = extract_file_name(prompt=user_prompt);
        #print("The class name is ", class_name);
        #print("The file name is ", file_name);
        if(class_name == None):
            print("You are trying to do file modification by adding a function to a class. "
                   "This requires specifying the name of the class into which the change has to be made")
            sys.exit();

    #log(f"[INFO] task_type = {task_type}")

    if task_type == "ADD_CLASS_METHOD":
        result = handle_add_class_method(user_prompt=user_prompt,
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
        return result
