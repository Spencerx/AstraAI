import ollama

# create persistent client once
client = ollama.Client(host="http://localhost:11434")

def run_ollama(prompt: str, model: str, seed: int = 42) -> str:

    response = client.generate(
        model=model,
        prompt=prompt,
        stream=False,
        options={
            "temperature": 0.0,
            "top_p": 1,
            "top_k": 1,
            "seed": seed,
            "num_thread": 1
        }
    )

    return response["response"].strip()

