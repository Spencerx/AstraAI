# Retrieval Augmented Generation (RAG)

This document describes how to perform retrieval augmented generation (RAG) with LLMs.

## Pre-requisite
1. Steps 1 and 2 in [Installing and building tools](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#installing-and-building-tools)
2. All steps in [Inference with LLM on Linux machine](https://github.com/AIModCon/modcon-hpc/tree/main/Inference#inference-with-llm-on-linux-machine)
3. All steps in [Make the LLM ollama-ready](https://github.com/AIModCon/modcon-hpc/tree/main/ModelFiles#make-the-llm-ollama-ready)
4. The source code should be commented sufficiently with metadata -- functions, features and any other info as deemed appropriate. An example of the metadata is shown in a cpp file in this folder.

## Inference with LLM + RAG

1. Get an interacitve node and start the ollama server
```
salloc --nodes 1 --qos interactive --time 04:00:00 --constraint gpu --gpus 1 --account=<account-id>
source ~/.bash_profile
source <path-to-modcon-env>/bin/activate 
ollama serve&
```

2. Extract the RAG metadata for the source code and write the `.json` file
```
python3 <path-to-RAG/extract_RAG_metadata_*.py> \
--embed-model=all-minilm \
--code-dir=<path-to-code-source-dir> \
--out-dir=<output-dir-for-rag-json-file>  
```
- Note: Ollama has the `all-minilm` embedding model within it.  
- `path-to-code-source-dir` is the path to the source code directory (all `*.cpp`, `*.f90`,`*.F90`, `*,h`, `*.H` files are parsed to extract RAG chunks).  
- `<output-dir-for-rag-json-file>` is the path to the directory to write the `*.json` file that will store the RAG chunks.
- For C++ codes, use `extract_RAG_metadata_cpp.py` and for Fortran codes, use `extract_RAG_metadata_fortran*.py`.

3. Run the python script for RAG.  
The following command is to run on terminal mode (`--terminal` option at the end of the command). The user prompt is given in a text file `user_prompt.txt`, and the output of the LLM+RAG inference is output to the terminal itself. 
```
python3 <path-to-/Tools/AstraAI_fortran/pr_watcher.py>
--llm-model=<llm-modelfile-for-ollama> \
--embed-model=all-minilm \
--rag-metadata-dir=<path-to-dir-with-json-file-with-rag-chunks> \
--top-k=2 \
--ollama-bin=<path-to-ollama/bin/ollama> \
--prompt-file=user_prompt.txt \
--terminal
```
  
To do the same in a GitHub PR mode, create a PR, and write a comment on the PR with 

```
python3 <path-to-/Tools/AstraAI_fortran/pr_watcher.py>
--llm-model=<llm-modelfile-for-ollama> \
--embed-model=all-minilm \
--rag-metadata-dir=<path-to-dir-with-json-file-with-rag-chunks> \
--top-k=2 \
--ollama-bin=<path-to-ollama/bin/ollama> \
--git-repo=<path-to-gi-repo>
```

- The `--llm-modelfile-for-ollama` is what was created using [Step 2 in this README](https://github.com/AIModCon/modcon-hpc/tree/main/Inference#2-load-the-model-into-ollama)  
- The `--ollama-bin` is the same as in [Step 2 in this README](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#2-install-and-configure-ollama)  
- The `--rag-metadata-dir` is the path to the directory that contains the `.json` file with the RAG chunks created in Step 2 above. 
- The `--git-repo` is the path to the github repository in the format `<username>/<repo-name>`
