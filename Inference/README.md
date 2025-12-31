# Inference with LLM on Linux machine 

## Pre-requisites: 
1. The [environment setup](https://github.com/AIModCon/modcon-hpc/tree/main?tab=readme-ov-file#environment-setup-on-linux) should be complete.

2. The llama.cpp and ollama should be installed (Steps 1 and 2 in [Install and building tools](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#installing-and-building-tools))

3. The model file should be ready (All steps in [Make the LLM ollama-ready](https://github.com/AIModCon/modcon-hpc/tree/main/ModelFiles#make-the-llm-ollama-ready))

Here are the steps to:
- Run inference on an interactive compute node

---

## 1. Get an interactive node and start the LLM runtime server

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

## 2. Load the model into Ollama

Create the Ollama model using the `Modelfile` from Step 2 in [ModelFiles README.md](https://github.com/AIModCon/modcon-hpc/tree/main/ModelFiles)

    ollama create my-ollama-model -f <path-to-modelfile-in-Step3>

This copies the GGUF model into Ollama’s model store.

---

## 3. Run the model and perform inference

Start an interactive inference session:

    ollama run my-ollama-model

You can now interact with the model via the command line.

