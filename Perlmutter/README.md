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

