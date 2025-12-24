# Running a Quantized LLM with llama.cpp and Ollama on HPC

This document describes the end-to-end workflow to:
- Build `llama.cpp`
- Convert a Hugging Face model to quantized GGUF format
- Register the model with Ollama
- Run inference on an interactive compute node

---

## 1. Get llama.cpp in the current directory

Run the provided script to clone and build `llama.cpp`:

    sh get_llama_cpp.sh

This typically takes about **10 minutes**.

---

## 2. Activate the ModCon environment and convert the Hugging Face model to GGUF

Activate the ModCon Python environment:

    source <path-to-modcon-env>/bin/activate

Convert the Hugging Face–downloaded model to **quantized GGUF (Q8_0)** format:

    python3 <path-to-llama.cpp>/convert_hf_to_gguf.py \
        <path-to-hugging-face-downloaded-model-dir> \
        --outfile model-q8_0.gguf \
        --outtype q8_0

This produces the file `model-q8_0.gguf`, which will be used by Ollama.

---

## 3. Create a Modelfile

Create a `Modelfile` (see example in this repository).

In the `FROM` line, point to the GGUF file generated in Step 2:

    FROM <path-to-model-q8_0.gguf>

You may optionally add system prompts or parameters as needed.

---

## 4. Install and configure Ollama

Run the Ollama install script:

    sh get_ollama.sh

Add the following lines to `~/.bash_profile`:

    alias ollama=<path-to-ollama>/bin/ollama
    export OLLAMA_MODELS=<path-in-scratch-for-ollama-model-storage>

Reload the profile so the changes take effect:

    source ~/.bash_profile

This ensures Ollama stores all models in scratch rather than `$HOME`.

---

## 5. Get an interactive node and start the LLM runtime server

Request an interactive GPU node:

    salloc --nodes 1 \
           --qos interactive \
           --time 04:00:00 \
           --constraint gpu \
           --gpus 1 \
           --account=<account-id>

Once on the node, initialize the environment and start the Ollama server:

    source ~/.bash_profile
    ollama serve &

After the server finishes initializing, press **Enter** to return to the command prompt.

---

## 6. Load the model into Ollama

Create the Ollama model using the `Modelfile` from Step 3:

    ollama create my-ollama-model -f <path-to-modelfile-in-Step3>

This copies the GGUF model into Ollama’s model store.

---

## 7. Run the model and perform inference

Start an interactive inference session:

    ollama run my-ollama-model

You can now interact with the model via the command line.

---

