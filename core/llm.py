import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3:mini"

def ask_llm_stream(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.7
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        stream=True
    )

    for line in response.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8"))
            if "response" in data:
                yield data["response"]
    