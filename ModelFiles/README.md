## 1. Activate the ModCon environment and convert the Hugging Face model to GGUF

Activate the ModCon Python environment:

    source <path-to-modcon-env>/bin/activate

Convert the Hugging Face–downloaded model to **quantized GGUF (Q8_0)** format:

    python3 <path-to-llama.cpp>/convert_hf_to_gguf.py \
        <path-to-hugging-face-downloaded-model-dir> \
        --outfile model-q8_0.gguf \
        --outtype q8_0

This produces the file `model-q8_0.gguf`, which will be used by Ollama.

---

## 2. Create a Modelfile

Create a `Modelfile` (see example in this repository).

In the `FROM` line, point to the GGUF file generated in Step 2:

    FROM <path-to-model-q8_0.gguf>

You may optionally add system prompts or parameters as needed.

