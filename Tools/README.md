# Installing and building tools 

This document describes the end-to-end workflow to:
- Get and build `llama.cpp`
- Get ollama
- Get aider (agent)

---

## 1. Get llama.cpp in the current directory
This is a framework that is required to convert the LLM to a specific format that is needed by the 
LLM runtime (See Step 2 below). 
Run the provided script to clone and build `llama.cpp`:

    sh get_llama_cpp.sh

This typically takes about 10 minutes.  
Note: This step currently works out of the box only on Perlmutter. The `llama.cpp/ggml/src/ggml_cuda/CMakeLists.txt` is tailored to Perlmutter (NERSC). For this to work on other machines, this `CMakeListst.txt` has to be modified to have the correct paths to the cuda libraries.

---

## 2. Install and configure Ollama
Ollama is a LLM runtime -- a local engine that runs language models (like GPT) on your machine or server so you can send prompts and get completions, without going through the cloud. It keeps the LLM loaded so it very much acts like a web based chatbot, but on your terminal.

Run the Ollama install script:

    sh get_ollama.sh

Add the following lines to `~/.bash_profile`:

    alias ollama=<path-to-ollama>/bin/ollama
    export OLLAMA_MODELS=<path-in-scratch-for-ollama-model-storage>

Reload the profile so the changes take effect:

    source ~/.bash_profile

This ensures Ollama stores all models in scratch rather than `$HOME`.

---

## 3. Install Aider agent 

This project uses **aider** as an AI coding assistant, backed by a **locally hosted LLM** served via **Ollama** using an OpenAI-compatible API.

Install aider using pip:

    pip install aider-chat

Add the following lines to `~/.bash_profile`:

    export OPENAI_API_BASE=http://localhost:11434/v1  
    export OPENAI_API_KEY=ollama

Reload the profile so the changes take effect:

    source ~/.bash_profile
