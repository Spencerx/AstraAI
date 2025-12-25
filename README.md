# AI4HPC using LLMs on Linux machines
This repository is aimed at developing a framework using large language models (LLM) 
on Linux machines and performing inference, RAG, Agentic AI, domain adaptive pre-training (DAPT), and fine-tuning. 

# Environment Setup on Linux

This README sets up a Python environment for running LLM models on a Linux filesystem. 
The Perlmutter scratch is chosen to do the installation.

```bash
# Create a folder for your environment and set up a virtual environment
mkdir -p $SCRATCH/mistral-env
python -m venv $SCRATCH/mistral-env

# Activate the environment
source $SCRATCH/mistral-env/bin/activate

# Configure Hugging Face cache
# Add the following to ~/.bash_profile
export HF_HOME=$SCRATCH/huggingface
source ~/.bash_profile
mkdir -p $HF_HOME

# Upgrade pip
pip install --upgrade pip

# Install PyTorch with CUDA support
pip install --prefix=$SCRATCH/mistral-env torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install Hugging Face libraries
pip install --prefix=$SCRATCH/mistral-env transformers accelerate bitsandbytes huggingface_hub

# Set PYTHONPATH (replace python3.10 with your Python version)
export PYTHONPATH=$SCRATCH/mistral-env/lib/python3.10/site-packages:$PYTHONPATH

# Verify installation
python -c "import torch; print(torch.cuda.is_available())"
python -c "import transformers; print(transformers.__version__)"

# Login to Hugging Face (see next section for details)
huggingface-cli login

# Download the Mistral model
huggingface-cli download mistralai/Mistral-7B-Instruct-v0.2 --local-dir <dir-to-install> --local-dir-use-symlinks False

# Optionally, set Hugging Face home to a persistent location
export HF_HOME=<path-to-hugging-face>/.hf
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
huggingface-cli login
```
Enter the token to login

# How to do inference
[See the README.md in the Inference directory.](https://github.com/AIModCon/modcon-hpc/tree/main/Inference)

# How to do fine tuning
[See the README.md in the FineTuning directory.](https://github.com/AIModCon/modcon-hpc/tree/main/FineTuning)


