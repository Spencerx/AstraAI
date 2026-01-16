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

# ${AGENT_NAME}

The agent description provides basic details about the agent service/system. This includes the agent’s purpose, how to interact with it (endpoint + I/O modes), declared capabilities/skills, and security/authentication requirements.

*Last Updated*: **2026-01-16**

## Developed by
Mahesh Natarajan, Xiaoye Li, Weiqun Zhang (Lawrence Berkeley National Laboratory)

## Contributed by
AMReX developers, HPC software engineers providing test cases and feedback.

## Agent Changelog
+ **2026-01-16** initial public version

## Agent short description
Tool-using AI assistant for HPC codebases, combining LLMs, retrieval, and AST-guided code edits for safe, context-aware code suggestions.

## Agent description
AstraAI interprets developer intent from terminal prompts or GitHub pull request comments, retrieves relevant HPC code examples via RAG, performs AST-based code analysis, and applies scoped code modifications. It enhances productivity while minimizing risk in complex HPC software workflows.

## Underlying model(s) (optional)
- Primary model(s): meta-llama/Llama-3.1-8B
- Any adapters/quantization/merges: N/A

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
  **Tags**: HPC, AMReX, C++, Fortran, GitHub  
  **Examples**:
    - Generate AMReX scaffolding for a new solver
    - Analyze and explain a compiler error  
  **Input/Output Modes**: text/plain / text/plain

### Tools and permissions
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

### Service endpoint and discovery
- Base URL: "local execution / CLI / GitHub PR watcher"
- A2A discovery path(s): N/A
- Invocation endpoint (example): CLI script or PR watcher Python process

## Runtime Infrastructure

### Hardware
Run on standard DOE HPC workstations or clusters; GPU recommended for LLM inference.

### Software
- Python 3.10+
- Ollama LLM runtime
- llama.cpp for model conversion
- Required Python packages: listed in requirements.txt

```txt
pip freeze > requirements.txt
```

## Papers and Scientific Outputs

N/A (planned SIAG LL4HPC conference submission)

## Agent License

Apache-2.0

## Contact Info and Card Authors

- Mahesh Natarajan (email@example.com)
- Xiaoye Li
- Weiqun Zhang

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




