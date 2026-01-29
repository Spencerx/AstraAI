# Make the LLM ollama-ready

## Pre-requisite:
1. The [environment setup](https://github.com/AIModCon/modcon-hpc/tree/main?tab=readme-ov-file#environment-setup-on-linux) should be complete.
2. The llama.cpp should be installed (Step 1 in [Install and building tools](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#installing-and-building-tools))

Here are the steps 
- The ollama LLM runtime requires the model to be in a .gguf format and 
- the modefile file. 

## 1. Convert the model from Hugging Face to GGUF

Activate the ModCon Python environment created in [Step 1 here](https://github.com/AIModCon/modcon-hpc/tree/main):

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

In the `FROM` line in this file (see example in this directory), point to the path of the GGUF file generated in Step 1 above:

    FROM <path-to-model-q8_0.gguf>

You may optionally add system prompts or parameters as needed.


## 3. Load the model into Ollama

Create the Ollama model using the `modelfile_for_ollama` from Step 2 in [Make the LLM ollama-ready](https://github.com/AIModCon/modcon-hpc/tree/main/ModelFiles)

    ollama create my-ollama-model -f <path-to-modelfile-for-ollama>

This copies the GGUF model into Ollama’s model store.
