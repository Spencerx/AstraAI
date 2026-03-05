import argparse
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_dir", required=True, help="Base model directory")
    parser.add_argument("--finetune_dir", required=True, help="LoRA finetuned adapter directory")
    args = parser.parse_args()

    # Load tokenizer from the base model
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)

    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        args.model_dir,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )

    # Load LoRA adapter
    model = PeftModel.from_pretrained(model, args.finetune_dir)

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

    # Save output
    with open("output.txt", "w") as f:
        f.write(code)

    print("Output saved to output.txt")


if __name__ == "__main__":
    main()

