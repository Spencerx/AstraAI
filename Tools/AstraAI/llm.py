import os
import subprocess

def run_ollama(prompt, model, ollama_bin="ollama"):
    env = os.environ.copy()
    env["OLLAMA_TEMPERATURE"] = "0"
    env["OLLAMA_TOP_P"] = "1"
    env["OLLAMA_TOP_K"] = "1"
    env["OLLAMA_LOG"] = "0"

    proc = subprocess.Popen(
        [ollama_bin, "run", model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        universal_newlines=True
    )

    stdout, stderr = proc.communicate(input=prompt)
    if proc.returncode != 0:
        print(f"[ERROR] Ollama failed:\n{stderr.strip() or stdout.strip()}")
        return None

    return stdout.strip()

