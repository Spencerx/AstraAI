# AstraAI on Perlmutter

On Perlmutter, the Python environment with all required packages is installed in the `m2957` project folder in `cfs`, so that all team members can access them without having to set up the environment themselves.  

Include the following lines in your `~/.bashrc` and then apply the changes:

```bash
export MODCON_ENV=/global/cfs/cdirs/m2957/nataraj2/modcon-env
alias ollama=/global/cfs/cdirs/m2957/nataraj2/Tools/ollama/bin/ollama
export OLLAMA_MODELS=/global/cfs/cdirs/m2957/nataraj2/Tools/ollama/ollama_models
export OPENAI_API_BASE=http://localhost:11434/v1
export OPENAI_API_KEY=ollama
export PYTHONPATH=/global/cfs/cdirs/m2957/nataraj2/modcon-env/lib/python3.11/site-packages:$PYTHONPATH
export HF_HOME=/global/cfs/cdirs/m2957/nataraj2/Tools/huggingface/cache
```

The do
`source ~/.bash_profile`

## Models

Some models are already existing in `/global/cfs/cdirs/m2957/nataraj2/Tools/ollama/ollama_models/manifests/registry.ollama.ai/library`.
For example `mistral7b-for-ollama`. The user can perform inference and all other workflows directly with the existing models.

## Inference

1. Request an interactive GPU node:
```
salloc --nodes 1 \
       --qos interactive \
       --time 04:00:00 \
       --constraint gpu \
       --gpus 1 \
       --account=<account-id>
```

2. Once on the node, initialize the environment and start the Ollama server:
```
source ~/.bash_profile
source <path-to-modcon-env>/bin/activate
ollama serve &
```

`<path-to-modcon-env>` is the path to the environment created in [Step 1 here](https://github.com/AIModCon/modcon-hpc/tree/main).
After the server finishes initializing, press **Enter** to return to the command prompt.

3. `ollama run mistral7b-for-ollama`
Now, the terminal behaves like a chatbot, and the user can type the prompt and get the response.


