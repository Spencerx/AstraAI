import openai
import os
import sys
import argparse

# ----------------------------
# Parse command line arguments
# ----------------------------
parser = argparse.ArgumentParser(description="Run CBorg model on a user prompt")
parser.add_argument("--amsc-model", type=str, required=True,
                    help="Name of the CBorg model to use")
parser.add_argument("--prompt-file", type=str, required=True,
                    help="Path to the prompt text file")

args = parser.parse_args()


# ----------------------------
# Read the full prompt from the file
# ----------------------------
try:
    with open(args.prompt_file, "r", encoding="utf-8") as f:
        full_prompt = f.read()
except FileNotFoundError:
    print(f"Error: Prompt file '{args.prompt_file}' not found.")
    sys.exit(1)

# ----------------------------
# Initialize CBorg client
# ----------------------------
client = openai.OpenAI(
    api_key=os.environ.get('AMSC_API_KEY'),  # API key from environment
    base_url="https://api.i2-core.american-science-cloud.org/"
)

models = client.models.list()

## Open a file in write mode
#with open("amsc_models_list.txt", "w", encoding="utf-8") as f:
#    for m in models.data:
#        f.write(m.id + "\n")   # Write each model ID on a new line

#print("Model list saved to amsc_models_list.txt")

# Assign command line values
models = [args.amsc_model]


# ----------------------------
# Run the model(s)
# ----------------------------
for m in models:
    try:
        response = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.0
        )
        print(f"Model: {m}\nResponse:\n{response.choices[-1].message.content}")
    except Exception as e:
        print(f"Error calling model {m}: {e}")
