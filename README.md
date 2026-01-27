# AI4HPC using LLMs on Linux machines
This repository is aimed at developing a framework using large language models (LLM) 
on Linux machines and performing inference, RAG, Agentic AI, and fine-tuning. 

# 1. Environment Setup on Linux

This README sets up a Python environment for running LLM models on a Linux filesystem. 
The installation has to be done in a directory with enough space (~2 TB). 

```bash
# Create a folder for your environment and set up a virtual environment
mkdir -p modcon-env
python -m venv modcon-env

# Activate the environment
source modcon-env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install PyTorch with CUDA support
pip install --prefix=modcon-env torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install Hugging Face libraries
pip install --prefix=modcon-env transformers accelerate bitsandbytes huggingface_hub

# Install required dependence sentencepiece
pip install sentencepiece

# Set PYTHONPATH (replace python3.10 with your Python version)
export PYTHONPATH=<path-to-modcon-env>/lib/python3.10/site-packages:$PYTHONPATH

# Verify installation
python -c "import torch; print(torch.cuda.is_available())"
python -c "import transformers; print(transformers.__version__)"

# Configure Hugging Face cache
# Add the following to ~/.bash_profile
export HF_HOME=<path-to-modcon-env>/huggingface/cache
source ~/.bash_profile
mkdir -p $HF_HOME

# Login to Hugging Face (see next section for details for hugging face authentication)
hf auth login

# Create a directory to store the hugging face models
mkdir <path-to-modcon-env>/huggingface/models

# Download the model of your choice from hugging face
# For example, to download the Mistral 7B model
hf download mistralai/Mistral-7B-Instruct-v0.2 --local-dir <path-to-modcon-env>/huggingface/models/<dir-to-install> 
```

## Hugging Face Authentication

To download LLMs available on Hugging Face, you need to authenticate with your Hugging Face account using an access token.

### 1. Create a Hugging Face account

If you don’t already have one, go to [https://huggingface.co/join](https://huggingface.co/join) and create an account.

### 2. Generate an access token

1. Go to [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)  
2. Click **“New token”**  
3. Give it a name (e.g., `scratch-access`) and select **read** scope (or `write` if needed).  
4. Copy the generated token.

### 3. Use the token to login

In your terminal (inside your virtual environment), run:

```bash
hf auth login
```
Enter the token to login

# 2. How to do inference?
[See Inference with LLM on Linux machine](https://github.com/AIModCon/modcon-hpc/tree/main/Inference#inference-with-llm-on-linux-machine)

# 3. How to do agentic coding?
[See Agent based coding](https://github.com/AIModCon/modcon-hpc/tree/main/AgenticAI#agent-based-coding)

# 4. How to do fine tuning?
[See the README.md in the FineTuning directory.](https://github.com/AIModCon/modcon-hpc/tree/main/FineTuning)


