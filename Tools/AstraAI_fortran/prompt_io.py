import os
import re
import sys

def read_user_prompt(prompt_file):
    if not os.path.exists(prompt_file):
        print(f"[ERROR] Prompt file {prompt_file} not found")
        sys.exit(1)

    with open(prompt_file, "r") as f:
        prompt = f.read().strip()

    if not prompt:
        print("[ERROR] Prompt file is empty")
        sys.exit(1)

    return prompt


def resolve_output_file(user_prompt):
    match = re.search(r'(\S+\.(?:cpp|cxx|cc|h|H|hpp))',
                      user_prompt, re.IGNORECASE)
    if not match:
        print("[ERROR] Could not determine output filename from prompt.")
        sys.exit(1)

    output_file = match.group(1)
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    print(f"Target file: {output_file}")

    return output_file

