import os
import json
from datasets import load_dataset, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model
from transformers import BitsAndBytesConfig

# -------------------------
# 1. Load dataset
# -------------------------

DATA_PATH = "./InstructionResponsePairs/amrex_dataset.jsonl"
print(f"Loading dataset manually: {DATA_PATH}")

train_data = []
with open(DATA_PATH, "r") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        train_data.append(obj)

print("Loaded examples:", len(train_data))
print("First example:", train_data[0])

# Convert to HuggingFace Dataset
train_dataset = Dataset.from_list(train_data)

print("Converted to HuggingFace dataset")

# -------------------------
# 2. Load tokenizer & model
# -------------------------

BASE_MODEL = "/pscratch/sd/n/nataraj2/mistral-7b"

bnb_config = BitsAndBytesConfig(
    load_in_8bit=True,
    llm_int8_threshold=6.0,
)

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("Loading model (8-bit)...")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto"
)

# -------------------------
# 3. Configure LoRA
# -------------------------

lora_config = LoraConfig(
    r=8,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# -------------------------
# 4. Tokenization function
# -------------------------

def build_prompt(instruction, response):
    return f"Instruction:\n{instruction}\n\nResponse:\n{response}"

def tokenize(example):
    prompt = build_prompt(example["instruction"], example["response"])
    t = tokenizer(
        prompt,
        truncation=True,
        max_length=2048,
        padding="max_length"
    )

    # --------- IMPORTANT FIX ---------
    pad_id = tokenizer.pad_token_id
    labels = t["input_ids"].copy()
    labels = [(x if x != pad_id else -100) for x in labels]
    t["labels"] = labels
    # ---------------------------------

    return t

print("Tokenizing dataset...")
tokenized_dataset = train_dataset.map(tokenize, batched=False)

# -------------------------
# 5. Training configuration
# -------------------------

training_args = TrainingArguments(
    output_dir="./amrex-lora-out",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=1,
    warmup_steps=5,
    max_steps=80,                # safer for tiny dataset
    learning_rate=5e-5,          # reduce LR to avoid collapse
    fp16=True,
    logging_steps=5,
    save_steps=80,
    save_total_limit=1,
    remove_unused_columns=False
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset
)

print("Starting training...")
trainer.train()

# -------------------------
# 8. Save LoRA outputs
# -------------------------

SAVE_DIR = "./amrex-lora"
print(f"Saving LoRA adapter to: {SAVE_DIR}")

model.save_pretrained(SAVE_DIR)
tokenizer.save_pretrained(SAVE_DIR)

print("Done.")
