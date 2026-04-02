# AstraAI 
AstraAI is aimed at developing a CLI framework using large language models (LLM) on Linux machines to perform inference enhanced with context-aware (Retrieval Augmented Generation based extraction) and structure aware (Abstract Syntax Tree based extraction) information for high performance computing codebases in C++ and Fortran. The repository also has the capabity to perform fine-tuning of models downloaded from Hugging Face.

# 1. Environment Setup on Linux

This section give the details to set up the Python environment for running LLM models on a Linux filesystem. The installation has to be done in a directory with enough space (~2 TB). 

```bash
# Create a folder for your environment and set up a virtual environment
module load python (or equivalent)
mkdir -p modcon-env
python -m venv modcon-env

# Activate the environment
source <path-to-modcon-env>/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install PyTorch with CUDA support
pip install --prefix=<path-to-modcon-env> torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 

# Install Hugging Face libraries
pip install --prefix=<path-to-modcon-env> transformers accelerate bitsandbytes huggingface_hub sentencepiece requests

# Set PYTHONPATH (replace python3.10 with your Python version)
export PYTHONPATH=<path-to-modcon-env>/lib/python3.10/site-packages:$PYTHONPATH

# Verify installation
python -c "import torch; print(torch.cuda.is_available())"
python -c "import transformers; print(transformers.__version__)"

# Configure Hugging Face cache
# Add the following to ~/.bash_profile
export HF_HOME=<path-to-huggingface>/cache
source ~/.bash_profile
mkdir -p $HF_HOME

# Login to Hugging Face (see next section for details for hugging face authentication)
hf auth login

# Create a directory to store the hugging face models
mkdir <path-to-huggingface>/models

# Download the model of your choice from hugging face
# For example, to download the Mistral 7B model
hf download mistralai/Mistral-7B-Instruct-v0.2 --local-dir <path-to-huggingface>/models/<dir-to-install>

# Install clang tools for python
pip install libclang
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

# 2. How to perform basic inference?
The basic inference that converts the terminal to a chatbot can be performed using models downloaded from Hugging Face or using any API. Examples using API are given for the CBorg API at Berkeley Lab, and the American Science Cloud API.  
[See Inference](https://github.com/AIForHPC/AstraAI/tree/main/Inference#inference-with-llm-on-linux-machine)

# 3. How to perform inference with LLM + RAG  + AST?
This repository has the capability to perform inference with context-aware (Retrieval Augmented Generation based extraction) and structure aware (Abstract Syntax Tree based extraction) information appended to the user prompt.  
[See Perlmutter](https://github.com/AIForHPC/AstraAI/tree/main/Perlmutter)  
Please note that some of the instructions are machine specific.


# 4. How to fine tune a model?
There are routines that can perform fine tuning of models downloaded from [Hugging Face](https://huggingface.co/join)  
[See FineTuning](https://github.com/AIForHPC/AstraAI/tree/main/FineTuning)

# Copyright Notice
AstraAI Copyright (c) 2026, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of
any required approvals from the U.S. Dept. of Energy). All rights reserved.

If you have questions about your rights to use or distribute this software,
please contact Berkeley Lab's Intellectual Property Office at
IPO@lbl.gov.

NOTICE.  This Software was developed under funding from the U.S. Department
of Energy and the U.S. Government consequently retains certain rights.  As
such, the U.S. Government has been granted for itself and others acting on
its behalf a paid-up, nonexclusive, irrevocable, worldwide license in the
Software to reproduce, distribute copies to the public, prepare derivative
works, and perform publicly and display publicly, and to permit others to do so.

Please see the copyright notice at [Legal.txt](https://github.com/AIForHPC/AstraAI/blob/main/Legal.txt)

# License
The license for AstraAI can be found in [license.txt](https://github.com/AIForHPC/AstraAI/blob/main/license.txt)

# Citation
To cite AstraAI, please use the [arxiv paper](https://arxiv.org/abs/2603.27423)
```
@misc{natarajan2026astraaillmsretrievalastguided,
      title={AstraAI: LLMs, Retrieval, and AST-Guided Assistance for HPC Codebases}, 
      author={Mahesh Natarajan and Xiaoye Li and Weiqun Zhang},
      year={2026},
      eprint={2603.27423},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2603.27423}, 
}
```




