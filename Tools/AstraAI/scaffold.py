import os
import shutil

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
