export OLLAMA_VERSION=0.13.2
wget https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tgz -O ollama-linux-amd64.tgz
tar xvf ollama-linux-amd64.tgz
mkdir ollama
mv bin lib ollama

