# Installing and building tools 

This document describes the end-to-end workflow to:
- Get and build `llama.cpp`
- Get ollama
- Get aider (agent)

---

## 1. Get llama.cpp in the current directory

Run the provided script to clone and build `llama.cpp`:

    sh get_llama_cpp.sh

This typically takes about **10 minutes**.

---

## 2. Install and configure Ollama

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
