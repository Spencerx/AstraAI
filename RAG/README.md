# Retrieval Augmented Generation (RAG)

This document describes how to perform retrieval augmented generation (RAG) with LLMs.

## Pre-requisite
1. Steps 1 and 2 in [Installing and building tools](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#installing-and-building-tools)
2. All steps in [Inference with LLM on Linux machine](https://github.com/AIModCon/modcon-hpc/tree/main/Inference#inference-with-llm-on-linux-machine)
3. All steps in [Make the LLM ollama-ready](https://github.com/AIModCon/modcon-hpc/tree/main/ModelFiles#make-the-llm-ollama-ready)

1. Get an interacitve node and start the ollama server
```
salloc --nodes 1 --qos interactive --time 04:00:00 --constraint gpu --gpus 1 --account=<account-id>
source ~/.bash_profile
source $SCRATCH/mistral-env/bin/activate 
ollama serve&
```

2. Extract the RAG metadata for the source code and write the `.json` file
```
python3 <path-to-modcon-hpc/Tools/extract_RAG_metadata.py> --code-dir=<path-to-code-source-dir> --out-dir=<output-dir-for-json-file> --embed-model=nomic-embed-text
```
Note: Ollama has the `nomic-embed-text` model within it, so the above should work.

3. Run the python script for RAG. Running this script will give a prompt at which the user can give code specific queries.

```
python3 <path-to-modcon-hpc/Tools/run_LLM_RAG.py> --llm-model=<path-to-my-ollama-model> --embed-model=nomic-embed-text --rag-dir=<path-to-dir-with-json-file> --top-k=5 --ollama-bin=<path-to-ollama-binary>
```
 The `--llm-model` is what was created using [Step 2 in this README](https://github.com/AIModCon/modcon-hpc/tree/main/Inference#2-load-the-model-into-ollama)  
 The `--ollama-bin` is the same as in [Step 2 in this README](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#2-install-and-configure-ollama)
