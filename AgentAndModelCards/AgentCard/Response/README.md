---
language:
- en # ISO language tag
tags:
- project:genesis # include on all GENESIS project models
- team:model_team_name # include your _short_ model team name e.g. MOAT
- type:agent # use other types include {agent, eval, framework, model, etc...}
- science:lightsource # what kind of science is this for (e.g., materials, biology, lightsource, fusion, climate, etc.)
- risk:general # indicates level of risk review {general, reviewed, restricted}
license: {spdx_license_id} # use an SPDX license identifier https://spdx.org/licenses/
license_name: {license_name}  # If license = other (license not in https://hf.co/docs/hub/repositories-licenses), specify an id for it here, like `my-license-1.0`. if not delete this line
license_link: {license_link}  # If license = other, specify "LICENSE" or "LICENSE.md" to link to a file of that name inside the repo, or a URL to a remote file. if not delete this line

# NOTE: base_model/datasets/metrics can still be used to describe the *underlying model(s)* this agent relies on.
base_model: {base_model} # if agent wraps one or more models, list the primary/base model URL here
new_version: meta-llama/Llama-3.1-8B # if this agent has been superseded by a new version, omit for now
datasets:
    - # optional: knowledge sources, training datasets for underlying models, or evaluation datasets for the agent
metrics:
    - # optional: metrics used to monitor and evaluate the agent in production or test runs

# Agent discovery + interoperability metadata
agent_card:
  name: "{agent_name}"                  # Human-readable name for the Agent (e.g., "Recipe Agent")
  description: "{agent_description}" # Human-readable description of the Agent's function 
  provider:                                       # Service provider information for the Agent
    organization: "{provider_organization}"
    url: "{agent_base_url}"                # Base URL where the agent is hosted
  version: "{agent_version}"             # Agent implementation version (e.g., 1.0.0)
  documentation_url: "{docs_url}"    # optional
  protocol_version: "{a2a_protocol_version}" # e.g., 0.3.0 (if applicable)
  preferred_transport: "JSONRPC"  # e.g., JSONRPC
  capabilities:                                    # Optional capabilities supported by the Agent
    streaming: false                           # If the Agent supports SSE 
    push_notifications: false              # If the Agent can push update notifications to the client 
    state_transition_history: false     # If the Agent exposes task state change history

# Authentication requirements for the Agent (intended to match OpenAPI auth structure) 
authentication: 
  schemes: 
    - "Bearer"                # e.g., Basic, Bearer 
  credentials: ""            # Credentials for the client to use for private cards (leave blank for public)

  # Defaults (can be overridden per-skill)
  default_input_modes:
    - "text/plain"
  default_output_modes:
    - "text/plain"

  # Skills: capability units exposed to users/other agents
  skills:
    - id: "{skill_id}"
      name: "{skill_name}"
      description: "{skill_description}"
      tags: []
      examples: []
      input_modes: []
      output_modes: []

# BPSW-only additions are explicitly separated as extensions.
Extensions:    # Optional operational metadata 
  agent_runtime:
    framework: "{framework_name}"                     # e.g., LangGraph / ADK / custom
    service_endpoint: "{service_endpoint_url}"     # A2A or API endpoint for invocation
    rate_limits: ""                                                   # optional
    logging: ""                                                        # optional (what is logged, where)
    memory: ""                                                      # optional (stateless/stateful, retention)

---

# ${AGENT_NAME}

The agent description provides basic details about the agent service/system. This includes the agent’s purpose, how to interact with it (endpoint + I/O modes), declared capabilities/skills, and security/authentication requirements.

*Last Updated*: **YYYY-MM-DD**

## Developed by

(a person or group that was primarily responsible for the creation and design of the model. It suggests a leading role in the research, coding, testing, and refinement processes.)

## Contributed by

(a person or group provided input or support to the model's development but may not have been the primary creator. Contributions can include data collection, analysis, theoretical insights, or minor modifications. This suggests collaboration, where multiple parties might have played various roles in the model's overall development.)

## Agent Changelog

+ **YYYY-MM-DD** initial public version

## Agent short description

Examples:

+ Tool-using assistant that routes tasks to specialized skills (e.g., retrieval, analysis, report generation), exposed via A2A/HTTP.
+ Agent that performs {TASK} by invoking {TOOLS} under {POLICY} constraints.

## Agent description

Examples:

1. The agent receives a user request, selects an appropriate skill, and (optionally) invokes tools to complete the task.
2. The agent can be deployed as a network service and discovered by other agents using an Agent Card.

## Underlying model(s) (optional)

- Primary model(s): {model_1}, {model_2}, ...
- If applicable, parent model(s): {base_model}
- Any adapters/quantization/merges: {details}

If you don’t want to specify the underlying model(s): 
- write `N/A` (e.g., `Primary model(s): N/A`)

## Inputs and outputs

(text, images, time series, etc.)

Examples of Inputs and Outputs:

1. Input: The agent accepts a user message (text) and optional structured parameters.
2. Output: The agent returns a response message and may return artifacts (files / structured data / references).

### Default interaction modes

- defaultInputModes: {e.g., ["text/plain"]}
- defaultOutputModes: {e.g., ["text/plain"]}
- If you support multiple modalities, list the MIME types here (e.g., `image/png`, `application/json`, etc.).

### Skills

List the skills this agent exposes:

- **Skill ID**: {skill_id}  
  **Name**: {skill_name}  
  **Description**: {skill_description}  
  **Tags**: {tags}  
  **Examples**: {examples}  
  **Input/Output Modes (optional overrides)**: {input_modes}/{output_modes}

### Tools and permissions

Describe the tools the agent can invoke and any permissions/side effects:

- Tool: {tool_name}
  - Purpose: {purpose}
  - Inputs: {inputs}
  - Outputs: {outputs}
  - Side effects: {none | reads data | writes data | network calls | executes jobs | ...}
  - Required permissions: {auth scopes / roles / policies}

### Service endpoint and discovery

- Base URL: `{agent_base_url}`
- A2A discovery path(s): `/.well-known/agent.json` and/or `/.well-known/agent-card.json`
- Invocation endpoint (example): `{service_endpoint_url}`

## Runtime Infrastructure

Example: This agent is deployed as a service (container, VM, or serverless runtime).

### Hardware

Please include a link to the DOE resource(s) used for hosting (if relevant)

### Software

Example: This agent was deployed with {framework/runtime}. Please attach packages via conda list or pip list or container initialization script.

Code snippets for getting configurations:

if Python: pip freeze > requirements.txt  
if Spack: provide a spack lock file  
if Conda: conda list --explicit > spec-file.txt  
if docker: Include docker file and docker compose script if needed  
else, another software package is used, please include reproducibility steps

```txt
put output or link to output here of the above commands
```

## Papers and Scientific Outputs

Citations in [bibtex format](https://www.bibtex.com/g/bibtex-format/). Please include either a `doi` or `url` field in the citation.

## Agent License

If using a non-standard license, please include it or a link to it here.

## Contact Info and Card Authors

Provide one or more corresponding authors with emails.

# Intended Uses

This section describes the use cases the agent is intended for, including the languages and domains where it can be applied. Document areas that are out of scope or where performance may be limited.

## Intended Use

Cases/examples/tasks for which the agent was intended to be used.

### Primary Intended Users

Example: The agent will be used by researchers to support scientific workflows requiring tool use and task delegation.

### Mission Relevance

This could include tasks linked to DOE projects or internal/external funded work.

## Out-of-Scope Use Cases

Describe cases not recommended for this agent’s use.

# How to use

This section is the most important for reusability of the agent. This section should include:

## Install Instructions

## Agent configuration

- System/prompt instructions location
- Tool configuration (API keys, endpoints, scopes)
- Policy configuration (allowed tools, rate limits, data access)
- Memory/state configuration (if applicable)

## Invocation / integration

- How to call the agent (CLI, SDK, HTTP, A2A JSON-RPC)
- How to pass inputs (text vs structured parts)
- How to retrieve artifacts

# Code snippets of how to use the agent

Include code for running the agent, calling its endpoint, and example payloads (including skill selection if applicable).

# Limitations

## Risks

> The most powerful AI systems may pose novel national security risks in the near future in areas
> such as cyberattacks and the development of chemical, biological, radiological, nuclear, or
> explosives (CBRNE) weapons, as well as novel security vulnerabilities. Because America
> currently leads on AI capabilities, the risks present in American frontier models are likely to be
> a preview for what foreign adversaries will possess in the near future. Understanding the
> nature of these risks as they emerge is vital for national defense and homeland security.

From the AI Action Plan, please document risks associated with your model consistent with this definition, if they exist

### Agent-specific risk notes (tool use)

- Risks from tool invocation / side effects (e.g., running jobs, modifying data, external calls)
- Prompt injection / tool hijacking considerations
- Data exfiltration / secrets handling considerations

## Limitations

Any additional concerns, or tests/data needed. Please include discussion of potential biases and systematic errors.

Other relevant cases not covered by the testing data data

Examples:

Like other large language models for which the homogeneity (or lack thereof) of training data induces downstream impact on the quality of our model, OPT-175B has limitations. OPT-175B can also have quality issues in terms of generation homogeneity and hallucination. In general, OPT-175B is not immune from the plethora of issues that plague modern large language models.

# Agent evaluation details (optional)

- Task success criteria (per-skill)
- Tool-call correctness / safety checks
- Latency, cost, and rate-limit behavior
- Human-in-the-loop requirements (if any)
- Regression tests for prompts/tool schemas

# More Information (optional)

Anything else you think it is important to communicate, but doesn't clearly fit under any other heading
