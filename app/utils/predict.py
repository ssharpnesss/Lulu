import re
import json
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel
from huggingface_hub import hf_hub_download

REPO = "SafeTechDev/Russian-Spam-classifier"
device = "cuda" if torch.cuda.is_available() else "cpu"

# ── Архитектура ──────────────────────────────────────────────────────────
class BinaryModel(nn.Module):
    def __init__(self, model_name):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name, low_cpu_mem_usage=True)
        hidden = self.bert.config.hidden_size
        self.binary = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(hidden, 1)
        )

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.last_hidden_state[:, 0]
        return self.binary(pooled).squeeze(-1)

# ── Загрузка ─────────────────────────────────────────────────────────────
config_path = hf_hub_download(REPO, "config.json", local_dir="./models_hf")
weights_path = hf_hub_download(REPO, "pytorch_model.bin", local_dir="./models_hf")

with open(config_path, encoding="utf-8") as f:
    cfg = json.load(f)

MAX_LENGTH = cfg.get("max_length", 40)

tokenizer = AutoTokenizer.from_pretrained(REPO)

model = BinaryModel(cfg["model"]).to(device)
model.load_state_dict(torch.load(weights_path, map_location=device, weights_only=True))
model.eval()

# ── Инференс ─────────────────────────────────────────────────────────────
def classify(text: str) -> dict:
    enc = tokenizer(
        text, truncation=True, padding="max_length",
        max_length=MAX_LENGTH, return_tensors="pt"
    )
    with torch.no_grad():
        logits = model(enc["input_ids"].to(device), enc["attention_mask"].to(device))

    prob_spam = float(torch.sigmoid(logits).squeeze().cpu().item())
    label = "SPAM" if prob_spam >= 0.9 else "SAFE"
    print(prob_spam, label)
    return {"label": label, "prob_spam": prob_spam}