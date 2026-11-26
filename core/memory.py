import json
import os

MEMORY_FILE = "data/memory.json"


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"facts": {}, "history": []}

    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {"facts": {}, "history": []}

    # 🛡 SAFETY: force correct structure
    if not isinstance(data, dict):
        return {"facts": {}, "history": []}

    data.setdefault("facts", {})
    data.setdefault("history", [])

    return data


def save_memory(memory: dict):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


# -------- CHAT HISTORY --------
def save_message(role: str, content: str):
    memory = load_memory()
    memory["history"].append({
        "role": role,
        "content": content
    })
    save_memory(memory)


def get_history():
    memory = load_memory()
    lines = []

    for msg in memory["history"][-10:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")

    return "\n".join(lines)


# -------- FACTS --------
def save_user_name(name: str):
    memory = load_memory()
    memory["facts"]["user_name"] = name.strip()
    save_memory(memory)


def get_user_name():
    memory = load_memory()
    return memory["facts"].get("user_name")
