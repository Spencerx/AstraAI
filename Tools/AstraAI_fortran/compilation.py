from typing import Optional, Callable

def build_compilation_prompt(compiler_output: str) -> str:
    return (
    "You are an expert C++ / HPC / AMReX developer.\n\n"
    "You will be given compiler or linker errors.\n"
    "Your job is to diagnose and fix them with MINIMAL text.\n\n"

    "OUTPUT FORMAT (strictly follow):\n"
    "ROOT CAUSE: <one sentence>\n"
    "FIX: <exact code change or build change>\n"
    "WHY: <one short sentence>\n\n"

    "Rules:\n"
    "- Be extremely concise.\n"
    "- No paragraphs.\n"
    "- No long explanations.\n"
    "- No restating the compiler output.\n"
    "- Do NOT rewrite entire files.\n"
    "- Assume the user is an experienced HPC developer.\n\n"

    "Compiler output:\n"
    "----------------\n"
    f"{compiler_output}\n"
    "----------------\n"
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



