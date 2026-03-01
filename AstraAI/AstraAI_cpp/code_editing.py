import shutil

def write_file_with_backup(path, new_content):
    shutil.copy2(path, path + ".bak")
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

def build_conflict_block(original_fn, generated_fn):
    return (
        "<<<<<<< CURRENT CODE\n"
        + original_fn.rstrip() + "\n"
        "=======\n"
        "<<<<<<< ASTRAAI CODE\n"
        + generated_fn.rstrip() + "\n"
        ">>>>>>> ASTRAAI\n"
    )

def apply_conflict_patch(source_file, code, start_offset, end_offset, generated_fn):
    original_fn = code[start_offset:end_offset]

    conflict_block = build_conflict_block(original_fn, generated_fn)

    updated_code = (
        code[:start_offset]
        + conflict_block
        + code[end_offset:]
    )

    write_file_with_backup(source_file, updated_code)

    return updated_code


