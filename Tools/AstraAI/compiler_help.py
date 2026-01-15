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

