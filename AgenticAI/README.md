# Agent based coding
This project uses [**aider**](https://github.com/Aider-AI/aider) as an AI coding assistant, backed by a **locally hosted LLM** served via **Ollama** using an OpenAI-compatible API. 
1. The agent works based on git. So, the local code that you are working with should be on GitHub (the aider agent looks for `.git` files).
2. The agent can modify files on disk (unlike the inference with LLM which gives its response only on the terminal). When you ask the agent to write code, you can prompt it as 
```
Add a function in src/compute.cpp which takes 2 real numbers as arguments and finds their sum. 
```
This will modify the file with the function.

## Pre-requisite
1. All steps in [Installing and building tools](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#installing-and-building-tools)
2. All steps in [Inference with LLM on Linux machine](https://github.com/AIModCon/modcon-hpc/tree/main/Inference#inference-with-llm-on-linux-machine)
3. All steps in [Make the LLM ollama-ready](https://github.com/AIModCon/modcon-hpc/tree/main/ModelFiles#make-the-llm-ollama-ready)

## 1. To use the Aider agent via terminal
To use the agent for coding tasks, follow the steps below
```
sh run_interactive_GPU.sh
source ~/.bash_profile
source <path-to-modcon-env>/bin/activate
ollama serve&
aider --model openai/my-ollama-model
```
Now, you get the agent prompt, much similar to the LLM chatbot. 

## 2. To use the Aider agent via GitHub PR comments
To use the agent from GitHub conversations (ie. the comments in the PR), there is a [python script in the Tools directory](https://github.com/AIModCon/modcon-hpc/blob/main/Tools/pr_agent.py) 
of this repo that will help you do that. Follow the steps below.
```
sh run_interactive_GPU.sh
source ~/.bash_profile
source <path-to-modcon-env>/bin/activate
ollama serve&
```

`cd` into the code directory you are working with (has to be a git repo), and run the python script from there 
```
python3 <path-to-pr_agent.py>
```
This script runs periodically every 5 seconds and looks for the latest comment in the latest PR. It looks if the comments begin with either of the tags -- `/agent-build` or `/agent-coder`.
