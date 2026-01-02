# Agent based coding

## Pre-requisite
1. All steps in [Installing and building tools](https://github.com/AIModCon/modcon-hpc/tree/main/Tools#installing-and-building-tools)
2. All steps in [Inference with LLM on Linux machine](https://github.com/AIModCon/modcon-hpc/tree/main/Inference#inference-with-llm-on-linux-machine)
3. All steps in [Make the LLM ollama-ready](https://github.com/AIModCon/modcon-hpc/tree/main/ModelFiles#make-the-llm-ollama-ready)

## Aider agent

aider --model openai/my-ollama-model


## PR agent
To use the agent from GitHub conversations (comments in the PR), there is a [python script in the `Tools` directory](https://github.com/AIModCon/modcon-hpc/blob/main/Tools/pr_agent.py) 
of this repo that will help you do that. Follow the steps below.

```
sh run_interactive_GPU.sh
source ~/.bash_profile
source <path-to-modcon-env>/bin/activate
ollama serve&
```
Go into the repo of the code you are working with and run the python script from there 
```
python3 <path-to-pr_agent.py>
```
