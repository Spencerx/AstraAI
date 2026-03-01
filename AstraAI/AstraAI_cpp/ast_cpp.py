#!/usr/bin/env python3

import subprocess
import json
import os
import shlex
import re
from typing import List


def load_compile_flags(compile_commands_path: str, file_name: str) -> List[str]:
    """
    Extract relevant compilation flags for a given file from compile_commands.json
    """
    with open(compile_commands_path, "r") as f:
        commands = json.load(f)

    file_name = os.path.abspath(file_name)

    for entry in commands:
        if os.path.abspath(entry["file"]) == file_name:
            cmd = shlex.split(entry["command"])

            flags = [
                token
                for token in cmd
                if (
                    token.startswith("-I")
                    or token.startswith("-D")
                    or token.startswith("-std=")
                    or token == "-fopenmp"
                )
            ]

            return flags

    raise RuntimeError(f"No compile_commands.json entry found for {file_name}")


import subprocess
import re
from typing import List

def extract_member_variables(
    class_name: str,
    file_name: str,
    compile_commands_path: str
) -> List[str]:
    """
    Returns member variables of a C++ class as clean declarations.

    Example output:
        amrex::Vector<int> istep
        int max_step = std::numeric_limits<int>::max()
    """

    # Load compile flags for this file from compile_commands.json
    flags = load_compile_flags(compile_commands_path, file_name)

    # clang-query: bind each field to "f"
    query = f"""
set output print
match fieldDecl(hasAncestor(cxxRecordDecl(hasName("{class_name}")))).bind("f")
"""

    clang_cmd = ["clang-query", file_name, "--"] + flags

    #print("Running clang-query command:\n")
    #print(" ".join(clang_cmd))

    result = subprocess.run(
        clang_cmd,
        input=query.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True
    )

    output = result.stdout.decode()

    # Extract lines bound to "f"
    pattern = r'Binding for "f":\s*\n([^\n]+)'
    raw_fields = re.findall(pattern, output)

    cleaned_fields = []

    for field in raw_fields:
        # Remove only the leading <FieldDecl ...> AST info
        field = re.sub(r'^<FieldDecl[^>]*>\s*', '', field)

        # Remove trailing semicolon if present
        field = field.strip().rstrip(';')

        # Normalize whitespace
        field = re.sub(r'\s+', ' ', field)
        field = field + ";"

        cleaned_fields.append(field)

    return cleaned_fields

import subprocess
import re

def clang_query_span(filename, func, cls=None):
    """
    Return (source_file, start_line, start_col, end_line, end_col) of a function.
    - Checks class method if cls is provided
    - Always checks for free function
    - Automatically identifies the file where the function is defined
    """
    cmd = [
        "clang-query",
        filename,
        "--",
        "-std=c++17"
    ]

    matchers = []
    if cls:
        # class method first
        matchers.append(f'match cxxMethodDecl(hasName("{func}"), ofClass(hasName("{cls}"))).bind("fn")')

    # always try free function
    matchers.append(f'match functionDecl(hasName("{func}")).bind("fn")')

    for matcher in matchers:
        proc = subprocess.run(
            cmd,
            input="set output dump\n" + matcher,
            text=True,
            capture_output=True
        )
        out = proc.stdout

        # clang-query output example:
        # <Prob.H:10:1, line:30:1>
        m = re.search(r"<(.+?):(\d+):(\d+),\s*line:(\d+):(\d+)>", out)
        if m:
            source_file = m.group(1)
            start_line  = int(m.group(2))
            start_col   = int(m.group(3))
            end_line    = int(m.group(4))
            end_col     = int(m.group(5))
            return source_file, start_line, start_col, end_line, end_col

    return None

def linecol_to_offset(text, line, col):
    # ensure integers
    line = int(line)
    col  = int(col)

    lines = text.splitlines(keepends=True)
    return sum(len(lines[i]) for i in range(line-1)) + (col-1)

