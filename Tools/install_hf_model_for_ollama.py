#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path
import shutil
import time

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def run(cmd, env=None):
    print(f"\n[RUN] {' '.join(cmd)}\n")
    subprocess.run(cmd, check=True, env=env)


def extract_model_name(hf_model: str) -> str:
    # Extract the model name from HF repo string
    return hf_model.split("/")[-1]


def directory_nonempty(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def replace_from_line(modelfile_path: Path, gguf_path: Path):
    lines = modelfile_path.read_text().splitlines()
    new_lines = []
    for line in lines:
        if line.strip().startswith("FROM "):
            new_lines.append(f"FROM {gguf_path}")
        else:
            new_lines.append(line)
    modelfile_path.write_text("\n".join(new_lines) + "\n")


def source_modcon_env():
    modcon_env = os.environ.get("MODCON_ENV")
    if not modcon_env:
        sys.exit("ERROR: MODCON_ENV is not set")

    activate = Path(modcon_env) / "bin" / "activate"
    if not activate.exists():
        sys.exit(f"ERROR: Cannot find {activate}")

    # Capture environment after sourcing the virtualenv
    cmd = f"bash -c 'source {activate} && env'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    env = dict(
        line.split("=", 1)
        for line in result.stdout.splitlines()
        if "=" in line
    )

    # Respect HF_HOME if set in your environment
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        env["HF_HOME"] = hf_home
        print(f"[INFO] Using HF_HOME={hf_home}")
    else:
        print("[WARN] HF_HOME not set; using default ~/.cache/huggingface")

    # Disable symlink warnings (optional, safer on HPC)
    env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    return env


# ------------------------------------------------------------
# Ollama server handling
# ------------------------------------------------------------
def ensure_ollama_server(env, ollama_bin):
    try:
        subprocess.run(
            [ollama_bin, "list"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        print("[INFO] Ollama server is already running")
    except subprocess.CalledProcessError:
        print("[INFO] Ollama server not running; starting in background...")
        subprocess.Popen(
            [ollama_bin, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        print("[INFO] Waiting 5 seconds for Ollama server to start...")
        time.sleep(5)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--install-model", required=True)
    parser.add_argument("--model-install-dir", required=True)
    parser.add_argument("--llamacpp-dir", required=True)
    parser.add_argument("--modelfile_template", required=True)
    parser.add_argument("--ollama-modelfile-dir", required=True)
    parser.add_argument("--ollama-bin", required=True, help="Full path to ollama executable")

    args = parser.parse_args()

    hf_model = args.install_model
    model_name = extract_model_name(hf_model)

    model_install_dir = Path(args.model_install_dir).resolve()
    local_dir = model_install_dir / model_name

    llama_cpp_dir = Path(args.llamacpp_dir).resolve()
    convert_script = llama_cpp_dir / "convert_hf_to_gguf.py"

    modelfile_template = Path(args.modelfile_template).resolve()
    ollama_modelfile_dir = Path(args.ollama_modelfile_dir).resolve()
    ollama_modelfile_dir.mkdir(parents=True, exist_ok=True)

    ollama_bin = Path(args.ollama_bin).resolve()
    if not ollama_bin.exists():
        sys.exit(f"ERROR: Ollama executable not found at {ollama_bin}")

    gguf_path = local_dir / f"{model_name}.gguf"

    print(f"""
HF model              : {hf_model}
Extracted name        : {model_name}
HF local dir          : {local_dir}
GGUF output           : {gguf_path}
Ollama modelfile dir  : {ollama_modelfile_dir}
Ollama executable     : {ollama_bin}
""")

    # --------------------------------------------------------
    # Step 1: Activate MODCON env
    # --------------------------------------------------------
    env = source_modcon_env()

    # Ensure ollama_bin directory is in PATH for subprocess
    env["PATH"] = f"{ollama_bin.parent}:{env.get('PATH','')}"

    # --------------------------------------------------------
    # Step 2: HF download (skip if present)
    # --------------------------------------------------------
    local_dir.mkdir(parents=True, exist_ok=True)

    if directory_nonempty(local_dir):
        print(f"[SKIP] HF model already exists in {local_dir}")
    else:
        run([
            "hf", "download",
            hf_model,
            "--local-dir", str(local_dir)
        ], env=env)

    # --------------------------------------------------------
    # Step 3: Convert to GGUF
    # --------------------------------------------------------
    if not convert_script.exists():
        sys.exit(f"ERROR: Cannot find {convert_script}")

    run([
        "python3",
        str(convert_script),
        str(local_dir),
        "--outfile", str(gguf_path),
        "--outtype", "q8_0"
    ], env=env)

    # --------------------------------------------------------
    # Step 4: Create Ollama Modelfile
    # --------------------------------------------------------
    new_modelfile = ollama_modelfile_dir / f"modelfile-for-{model_name}"
    shutil.copy(modelfile_template, new_modelfile)
    replace_from_line(new_modelfile, gguf_path)

    print(f"[INFO] Created modelfile: {new_modelfile}")

    # --------------------------------------------------------
    # Step 5: Ensure Ollama server and create model
    # --------------------------------------------------------
    ensure_ollama_server(env, str(ollama_bin))

    ollama_model_name = f"{model_name}-for-ollama"
    run([
        str(ollama_bin), "create",
        ollama_model_name,
        "-f", str(new_modelfile)
    ], env=env)

    # --------------------------------------------------------
    # Step 6: Final completion message
    # --------------------------------------------------------
    print(f"\n✅ Ollama model created: {ollama_model_name}")
    print(f"\n🎉 {ollama_model_name} has been created and is ready to use!\n")


if __name__ == "__main__":
    main()
