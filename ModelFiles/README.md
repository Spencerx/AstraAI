# Make the LLM ollama-ready

## Pre-requisite:
1. The [environment setup](https://github.com/AIModCon/modcon-hpc/tree/main?tab=readme-ov-file#environment-setup-on-linux) should be complete.
2. The llama.cpp should be installed (Step 1 in [Install and building tools](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#installing-and-building-tools))

Here are the steps 
- The ollama LLM runtime requires the model to be in a .gguf format and 
- the modefile file. 

## Install Hugging Face Model for Ollama

Run the following command to download a model from Hugging Face, convert it via `llama.cpp`, and register it with `ollama`:

```bash
python3 install_hf_model_for_ollama.py \
    --install-model=deepseek-ai/deepseek-coder-6.7b-instruct \
    --model-install-dir=<path-to-huggingface-storage> \
    --llamacpp-dir=<path-to-llama-cpp-repo> \
    --modelfile_template=<path-to-modelfile-template> \
    --ollama-modelfile-dir=<path-to-ollama-modelfiles-output> \
    --ollama-bin=<path-to-ollama-binary>
```
The `--install-model` should be in the format `deepseek-ai/deepseek-coder-6.7b-instruct` -- like the usual hugging face models are named.

### Explanation

Running the above script does the 
1. Convert the model from Hugging Face to GGUF

Activate the ModCon Python environment created in [Step 1 here](https://github.com/AIModCon/modcon-hpc/tree/main):

    source <path-to-modcon-env>/bin/activate

Convert the Hugging Face–downloaded model to **quantized GGUF (Q8_0)** format:

    python3 <path-to-llama.cpp>/convert_hf_to_gguf.py \
        <path-to-hugging-face-downloaded-model-dir> \
        --outfile model-q8_0.gguf \
        --outtype q8_0

This produces the file `model-q8_0.gguf`, which will be used by Ollama.

---

2. Create a modelfile

Create a `modelfile_for_ollama` (see example in this directory).

In the `FROM` line in this file (see example in this directory), point to the path of the GGUF file generated in Step 1 above:

    FROM <path-to-model-q8_0.gguf>

You may optionally add system prompts or parameters as needed.


3. Load the model into Ollama

Create the Ollama model using the `modelfile_for_ollama` from Step 2 in [Make the LLM ollama-ready](https://github.com/AIModCon/modcon-hpc/tree/main/ModelFiles)

    ollama create my-ollama-model -f <path-to-modelfile-for-ollama>

This copies the GGUF model into Ollama’s model store.
