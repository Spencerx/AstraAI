---
language:
- en
tags:
- project:genesis
- team:moat
- type:agent
- science:computational-science
- risk:general
license: Apache-2.0

base_model: meta-llama/Llama-3.1-8B
new_version: meta-llama/Llama-3.1-8B
datasets:
    - N/A
metrics:
    - N/A

agent_card:
  name: "AstraAI"
  description: "An open-source, Copilot-like AI agent for HPC codebases combining LLMs, RAG, and AST-guided edits for context-aware, safe code suggestions."
  provider:
    organization: "Lawrence Berkeley National Laboratory"
    url: "https://github.com/your-repo/AstraAI"
  version: "0.1.0"
  documentation_url: "https://github.com/your-repo/AstraAI#readme"
  protocol_version: "0.1.0"
  preferred_transport: "JSONRPC"
  capabilities:
    streaming: false
    push_notifications: false
    state_transition_history: false

authentication: 
  schemes: 
    - "Bearer"
  credentials: ""
  default_input_modes:
    - "text/plain"
  default_output_modes:
    - "text/plain"

  skills:
    - id: "code_assist"
      name: "HPC Code Assistance"
      description: "Supports scaffolding, debugging, and code generation for scientific/HPC software projects."
      tags: [HPC, AMReX, C++, Fortran, GitHub]
      examples:
        - "Generate AMReX scaffolding for a new solver"
        - "Analyze and explain a compiler error"
      input_modes: ["text/plain"]
      output_modes: ["text/plain"]

Extensions:
  agent_runtime:
    framework: "Custom Python + LLM pipeline"
    service_endpoint: "local/cli execution or GitHub PR watcher"
    rate_limits: "None"
    logging: "Local console logs for actions; optional GitHub comment logs"
    memory: "Stateless; per-run context handled via terminal/PR input"

---

# AstraAI

*Last Updated*: **2026-01-16**

## Developed by
Mahesh Natarajan, Xiaoye Li (Lawrence Berkeley National Laboratory)

## Contributed by
No additional contributors.

## Agent Changelog
+ **2026-01-17** – Initial internal version (private repository)


## Agent short description
An agentic AI assistant for HPC codebases that combines LLMs, Retrieval-Augmented Generation (RAG), and Abstract Syntax Tree (AST)–guided code editing to produce safe, context-aware modifications.

## Agent description
AstraAI interprets developer intent from terminal prompts or GitHub pull request comments, retrieves relevant HPC code examples via RAG, and uses AST-based analysis to determine permissible code edit regions. The system constructs a structured LLM prompt that combines the user request, the target code fragment, retrieved context, and explicit editing constraints. The generated output is subsequently checked against AST and structural rules and applied as a scoped, syntax-preserving code modification, improving productivity while reducing risk in complex HPC software workflows.

## Underlying model(s) (optional)
The agent does not depend on a single fixed model. It supports interchangeable open-source LLM backends, including models distributed via Hugging Face, provided that the model weights or checkpoints can be downloaded and served locally.

## Inputs and outputs
1. Input: Text prompts from terminal or GitHub PR comments.
2. Output: Text/code responses, optionally modifying HPC code in a controlled manner.

### Default interaction modes
- defaultInputModes: ["text/plain"]
- defaultOutputModes: ["text/plain"]

### Skills
- **Skill ID**: code_assist  
  **Name**: HPC Code Assistance  
  **Description**: Supports scaffolding, debugging, and code generation for HPC software projects.  
  **Tags**: HPC, LLM, RAG, AST, C++, Fortran, GitHub  
  **Examples**:  
    -- Generate AMReX scaffolding for a new solver  
    -- Analyze and explain a compiler error  
    -- Add a member function to an existing class (e.g., `add computeEnergy(double mass, double velocity)` to `class Particle`) 
       and implement it in the corresponding `.cpp` file.  
  **Input/Output Modes**: text/plain / text/plain

### Tools and permissions
- Tool: Model and embedding repository (Hugging Face Hub)
  - Purpose: Source large language models and embedding models used by the agent
  - Inputs: Model identifiers, configuration files, tokenizer artifacts
  - Outputs: Model weights, tokenizers, embedding models
  - Side effects: Network access for model download (optional local caching)
  - Required permissions: Network access (read-only)

- Tool: Local LLM runtime (Ollama)
  - Purpose: Natural language understanding and code generation
  - Inputs: Prompts from terminal or PR
  - Outputs: Generated code suggestions or comments
  - Side effects: Executes local inference
  - Required permissions: Local execution

- Tool: Model conversion via llama.cpp
  - Purpose: Convert Hugging Face LLMs to GGUF for Ollama execution
  - Inputs: Pretrained Hugging Face model
  - Outputs: GGUF model file
  - Side effects: File conversion
  - Required permissions: Local execution

- Tool: GitHub API
  - Purpose: Read PR comments and post agent responses
  - Inputs: PR metadata, comments
  - Outputs: PR comments
  - Side effects: network calls
  - Required permissions: GitHub token (repo-scoped)

- Tool: Local file system and GPUs
  - Purpose: Generate or modify source files
  - Inputs: Prompt, templates
  - Outputs: Source code files
  - Side effects: writes data
  - Required permissions: filesystem access, compute time on GPU nodes

### Service endpoint and discovery
- Base URL: N/A (currently local/private use)
- A2A discovery path(s): N/A (not deployed)
- Invocation endpoint (example): N/A (currently invoked via Python scripts or CLI)

## Runtime Infrastructure

This agent (AstraAI) is designed for HPC codebases and combines Python-based LLM runtimes, Hugging Face models, AST-guided code analysis, and code editing tools. It has been tested on GPU-equipped HPC nodes and local workstations.

### Hardware
- GPU-enabled HPC cluster or workstation (CUDA 12.1 compatible)
- Local storage for model weights and Hugging Face cache

### Software
- **Python**: virtual environment created at `$SCRATCH/modcon-env`
- **Python packages installed via pip**:
  - `torch`, `torchvision`, `torchaudio` (CUDA 12.1)
  - `transformers`, `accelerate`, `bitsandbytes`, `huggingface_hub`

```bash
# Setup Python environment
mkdir -p $SCRATCH/modcon-env
python -m venv $SCRATCH/modcon-env
source $SCRATCH/modcon-env/bin/activate
pip install --upgrade pip
pip install --prefix=$SCRATCH/modcon-env torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install --prefix=$SCRATCH/modcon-env transformers accelerate bitsandbytes huggingface_hub
huggingface-cli login
huggingface-cli download mistralai/Mistral-7B-Instruct-v0.2 \
  --local-dir <dir-to-install> --local-dir-use-symlinks False
```
- **Ollama runtime**: For running Hugging Face models directly  
- **llama.cpp**: For converting Hugging Face models to GGUF for local deployment 
- **C++ AST**: Clang / LibTooling for parsing headers, classes, and functions for safe code edits  
- **Fortran AST**: fparser or OpenFortranParser, depending on target codebase  

## Papers and Scientific Outputs

1. Talk scheduled at the 2nd annual High Performance Software Foundation conference in Chicago on March 16-20, 2026.
2. Planned workshop paper submission in the 2nd International Workshop on Foundational Large Language Models Advances for HPC (LLM4HPC) to be held in conjunction with ISC-HPC 2026, June 26th, 2026, Hamburg, Germany

## Agent License

Apache-2.0

## Contact Info and Card Authors

- Mahesh Natarajan (MaheshNatarajan@lbl.gov)
- Xiaoye Li (xsli@lbl.gov)

## Intended Uses

### Intended Use

Accelerating HPC software development by providing safe, context-aware code suggestions and automated scaffolding for scientific solvers.

### Primary Intended Users

HPC developers and scientific software engineers working on AMReX or similar frameworks.

### Mission Relevance

DOE HPC projects, scientific software development workflows, and research reproducibility.

### Out-of-Scope Use Cases

- Non-HPC codebases
- End-user software outside scientific computing
- Production AI deployment without code review

## How to Use

### Install Instructions

Clone the repository, install dependencies from `requirements.txt`, and configure the local Ollama runtime.

### Agent Configuration

- System/prompt instructions in prompt files
- Tool configuration: local LLM runtime, model conversion via `llama.cpp`
- Policy configuration: scoped edits, RAG retrieval limits
- Memory/state: per-run session only

### Invocation / Integration

- **CLI execution**: terminal prompt mode
- **GitHub PR watcher**: polls PRs and comments every 5 seconds
- Outputs returned as code suggestions or PR comments

### Code Snippets of How to Use the Agent

```bash
python pr_watcher.py \
  --llm-model=my-ollama-model \
  --embed-model=nomic-embed-text \
  --rag-dir=./rag_metadata/ \
  --hpc-code-examples-dir=./tutorials/ \
  --terminal
```

# Limitations

## Risks

- Tool invocation can modify code; only safe scoped edits recommended  
- Potential for prompt injection via untrusted PR comments  
- Data exfiltration risk minimized by local execution only  

## Limitations

- AI suggestions may occasionally be incorrect or misaligned with project conventions  
- Currently supports HPC scientific code (C++/Fortran); extension to other languages may require retraining/adaptation  

# Agent Evaluation Details (Optional)

- **Task success**: correctness of code edits and compilability  
- **Tool-call correctness**: evaluation against test compilations  
- **Latency**: depends on local LLM inference speed  
- **Human-in-the-loop**: recommended for final code merges  
- **Regression tests**: automated tests on scaffolding and AST modifications  

# More Information (Optional)

- **Source repository**: [https://github.com/your-repo/AstraAI](https://github.com/your-repo/AstraAI)  
- **Model conversion instructions**: [https://github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)  
- **LLM runtime**: [https://ollama.ai](https://ollama.ai)  




