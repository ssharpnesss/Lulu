from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
model_path = project_root / "assets/ruspam_model"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)
model.eval()

def predict(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        predicted_class = torch.argmax(logits, dim=1).item()
    return predicted_class
