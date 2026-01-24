import os
import shutil
from typing import Optional, Callable, List
from scaffold_state import scaffold_exists, write_scaffold_state

def handle_scaffolding(
    *,
    user_prompt: str,
    pr: Optional[int],
    log: Callable,
    emit_response: Callable,
    hpc_examples_dir: str,
) -> None:

    log("[INFO] Handling scaffolding request")

    if scaffold_exists():
        log("[INFO] Scaffold already exists, skipping.")
        emit_response(pr, "⚠️ Scaffold already exists. Skipping.")
        return

    if not hpc_examples_dir:
        log("[ERROR] hpc-code-examples-dir required for scaffolding")
        emit_response(pr, "❌  hpc-code-examples-dir not configured.")
        return

    target_dir = "src"
    os.makedirs(target_dir, exist_ok=True)

    # Copy scaffold files
    added_files = copy_scaffold(hpc_examples_dir, target_dir)

    # Record scaffold metadata/state
    write_scaffold_state(
        scaffold_type=os.path.basename(hpc_examples_dir),
        intent="scaffolding",
        user_prompt=user_prompt,
    )

    # Emit response listing files added
    files_list_str = "\n".join(f"- `{f}`" for f in added_files)
    emit_response(
        pr,
        f"✅  Scaffold generated in `{target_dir}` with files:\n{files_list_str}",
    )


def copy_scaffold(examples_dir, target_dir="src") -> list:
    """
    Re-create the full directory structure from `examples_dir` into `target_dir`.

    - If `target_dir` exists, place scaffold inside it.
    - If it does not exist, create it.
    - All files and directories in examples_dir are copied recursively.
    - Returns a list of full paths of files that were actually copied.
    """
    if not os.path.exists(examples_dir):
        raise FileNotFoundError(f"Examples directory not found: {examples_dir}")

    # Ensure target_dir exists
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    added_files = []

    # Recursively copy all files and directories
    for root, dirs, files in os.walk(examples_dir):
        # Compute relative path from examples_dir
        rel_path = os.path.relpath(root, examples_dir)
        dest_path = os.path.join(target_dir, rel_path) if rel_path != "." else target_dir

        # Ensure directories exist
        os.makedirs(dest_path, exist_ok=True)

        # Copy files
        for file in files:
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_path, file)
            # Only overwrite if file doesn't exist
            if not os.path.exists(dest_file):
                shutil.copy2(src_file, dest_file)
                added_files.append(dest_file)

    return added_files
