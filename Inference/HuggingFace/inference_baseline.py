import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Generate text from a model")
parser.add_argument(
    "--model_dir",
    type=str,
    required=True,
    help="Path to the model directory"
)
args = parser.parse_args()

model_path = args.model_dir

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

# Read prompt from file
with open("prompt.txt", "r") as f:
    prompt = f.read()

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

outputs = model.generate(
    **inputs,
    max_new_tokens=3000,
    do_sample=False
)

code = tokenizer.decode(outputs[0], skip_special_tokens=True)

# Save output to file
with open("output.txt", "w") as f:
    f.write(code)

print("Output saved to output.txt")
