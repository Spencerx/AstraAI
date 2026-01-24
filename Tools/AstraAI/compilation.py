from typing import Optional, Callable

def build_compilation_prompt(compiler_output: str) -> str:
    """
    Build an LLM prompt for diagnosing compilation / linker errors.
    """
    return (
        "You are an expert C++ / HPC / AMReX developer.\n\n"
        "The following is compiler and linker output from a build.\n\n"
        "Your task:\n"
        "- Identify the ROOT CAUSE of the error\n"
        "- Explain WHY it is happening\n"
        "- Provide concrete steps to fix it\n"
        "- If relevant, suggest CMake / Makefile changes\n"
        "- Do NOT rewrite entire files\n\n"
        "Compiler output:\n"
        "----------------\n"
        f"{compiler_output}\n"
        "----------------\n\n"
        "Respond with clear, actionable guidance.\n"
    )

def handle_compilation(
    *,
    user_prompt: str,
    pr: Optional[int],
    log: Callable,
    run_llm: Callable,
    emit_response: Callable,
) -> None:

    """
    Diagnose compiler / linker errors using LLM.
    """

    log("[INFO] Handling compilation diagnostics")

    prompt = build_compilation_prompt(user_prompt)

    response = run_llm(prompt, pr)
    if not response:
        return

    emit_response(
        pr,
        "### 🧩 Compilation diagnostics\n\n" + response,
    )



