import requests
import json

url = "https://spam.sharpness.lol/classify"

def predict_spam(
    text: str,
    api_key: str
): 
    headers = {
        "X-API-Key": f"{api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "text": text
    }

    result = requests.post(
        url,
        headers=headers,
        json=data
    )

    return result.json()