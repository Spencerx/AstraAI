---
language:
- en
tags:
- project:genesis
- team:astraai
- type:agent
- science:climate
- risk:general
license: BSD-3-Clause
license_name: BSD 3-Clause License
license_link: LICENSE

base_model: mistral-7b (any model can be used)
new_version: 
datasets:
    - AMReX tutorials and example codes (curated)
metrics:
    - Task success (qualitative)
    - Correctness of generated code (manual review)
    - Compilation success rate (when applicable)

agent_card:
  name: "AstraAI"
  description: > 
An open-source, Copilot-like AI agent for HPC and scientific codebases that integrates 
large language models with Retrieval-Augmented Generation (RAG) and Abstract Syntax Tree (AST)–guided 
analysis to produce context-aware code suggestions and safely scoped GitHub pull request updates.
  provider:
    organization: "Lawrence Berkeley National Laboratory"
    url: "https://www.lbl.gov"
  version: "0.1.0"
  documentation_url: ""
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
      description: "Assists with code scaffolding, compilation diagnostics, and code generation for scientific/HPC applications."
      tags: ["HPC", "C++", "AMReX", "GitHub"]
      examples:
        - "@astraai generate an ErrorEst method for this AMReX solver"
        - "@astraai analyze this compilation error"
      input_modes:
        - "text/plain"
      output_modes:
        - "text/plain"

Extensions:
  agent_runtime:
    framework: "custom"
    service_endpoint: ""
    rate_limits: ""
    logging: "stdout, GitHub PR comments"
    memory: "stateless (per invocation)"

---

# AstraAI

The agent description provides basic details about the agent service/system. This includes the agent’s purpose, how to interact with it (endpoint + I/O modes), declared capabilities/skills, and security/authentication requirements.

*Last Updated*: **2026-01-15**

## Developed by

AstraAI core development team at Lawrence Berkeley National Laboratory.

## Contributed by

Contributors from the AMReX and ModCon communities, including domain scientists and HPC developers who provided feedback, test cases, and example workflows.

## Agent Changelog

+ **2026-01-15** initial public version

## Agent short description

+ Tool-using assistant that supports scientific and HPC code development by responding to GitHub PR comments or terminal-based prompts.
+ Agent that performs code scaffolding, compilation diagnostics, and code generation by invoking LLMs, with planned AST and RAG integration.

## Agent description

1. The agent monitors GitHub pull requests and responds to comments containing a trigger keyword, extracting user intent and producing context-aware responses.
2. The agent can also be invoked from the terminal as a CLI tool for local development workflows.
3. The agent routes tasks through a unified pipeline supporting intent detection, retrieval-augmented generation, and (planned) AST-based code analysis.

## Underlying model(s) (optional)

- Primary model(s): Local LLMs served via Ollama (e.g., LLaMA-family models)
- If applicable, parent model(s): meta-llama/Llama-3.x
- Any adapters/quantization/merges: Model-dependent, configured externally

## Inputs and outputs

Examples of Inputs and Outputs:

1. Input: A user request provided via GitHub PR comment or terminal prompt (text).
2. Output: A textual response containing explanations, diagnostics, or generated source code; may also produce files on disk in terminal mode.

### Default interaction modes

- defaultInputModes: ["text/plain"]
- defaultOutputModes: ["text/plain"]

### Skills

- **Skill ID**: code_assist  
  **Name**: HPC Code Assistance  
  **Description**: Supports scaffolding, debugging, and code generation for scientific/HPC software projects.  
  **Tags**: HPC, AMReX, C++, GitHub  
  **Examples**:  
  - Generate AMReX scaffolding for a new solver  
  - Analyze and explain a compiler error  
  **Input/Output Modes**: text/plain

### Tools and permissions

- Tool: GitHub API
  - Purpose: Read PR comments and post agent responses
  - Inputs: PR metadata, comments
  - Outputs: PR comments
  - Side effects: network calls
  - Required permissions: GitHub token (repo-scoped)

- Tool: Local file system
  - Purpose: Generate or modify source files
  - Inputs: Prompt, templates
  - Outputs: Source code files
  - Side effects: writes data
  - Required permissions: filesystem access

- Tool: Local LLM runtime (Ollama)
  - Purpose: Natural language understanding and generation
  - Inputs: Prompts
  - Outputs: Generated text/code
  - Side effects: executes local inference
  - Required permissions: local execution

### Service endpoint and discovery

- Base URL: N/A (local execution)
- A2A discovery path(s): N/A
- Invocation endpoint (example): CLI invocation or GitHub webhook polling

## Runtime Infrastructure

### Hardware

Typically executed on HPC login nodes or development workstations. DOE HPC systems (e.g., NERSC Perlmutter) may be used for development and testing.

### Software

- Python 3.x
- requests
- Ollama (local LLM runtime)

Reproducibility artifacts can be provided via:
- `pip freeze > requirements.txt`

```txt
requirements.txt (to be provided)

