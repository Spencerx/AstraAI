# Make the LLM ollama-ready

## Pre-requisite:
1. The [environment setup](https://github.com/AIModCon/modcon-hpc/tree/main?tab=readme-ov-file#environment-setup-on-linux) should be complete.
2. The llama.cpp should be installed (Step 1 in [Install and building tools](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#installing-and-building-tools))

Here are the steps 
- The ollama LLM runtime requires the model to be in a .gguf format and 
- the modefile file. 

## 1. Convert the model from Hugging Face to GGUF

Activate the ModCon Python environment:

    source <path-to-modcon-env>/bin/activate

Convert the Hugging Face–downloaded model to **quantized GGUF (Q8_0)** format:

    python3 <path-to-llama.cpp>/convert_hf_to_gguf.py \
        <path-to-hugging-face-downloaded-model-dir> \
        --outfile model-q8_0.gguf \
        --outtype q8_0

This produces the file `model-q8_0.gguf`, which will be used by Ollama.

---

## 2. Create a modelfile

Create a `modelfile_for_ollama` (see example in this directory).

In the `FROM` line, point to the GGUF file generated in Step 2:

    FROM <path-to-model-q8_0.gguf>

You may optionally add system prompts or parameters as needed.

