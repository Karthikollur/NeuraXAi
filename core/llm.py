import json

import requests

from core import config


def ask_llm_stream(prompt):
    payload = {
        "model": config.MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": config.TEMPERATURE
        }
    }

    response = requests.post(
        f"{config.OLLAMA_URL.rstrip('/')}/api/generate",
        json=payload,
        stream=True
    )

    for line in response.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8"))
            if "response" in data:
                yield data["response"]

