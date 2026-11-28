import json
import os
import tempfile
import threading
import time

from core import config


MEMORY_FILE = os.path.join(config.DATA_DIR, "memory.json")

# ponytail: one process-wide lock around every read-modify-write (D6).
# Fine for the single-process Flask server; Stage 5 replaces this with SQLite.
_LOCK = threading.RLock()


def _fresh():
    return {"facts": {}, "history": []}


def _is_valid(data) -> bool:
    # Missing keys are fine (setdefault fills them); wrong types are not.
    # Entries must carry what get_history() reads, or every turn would crash.
    if not isinstance(data, dict):
        return False
    if not isinstance(data.get("facts", {}), dict):
        return False
    history = data.get("history", [])
    return isinstance(history, list) and all(
        isinstance(m, dict) and "role" in m and "content" in m for m in history
    )


def _backup_corrupt(path):
    """Move an unreadable file aside so its bytes are never overwritten."""
    os.replace(path, f"{path}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}")


def load_memory():
    with _LOCK:
        path = MEMORY_FILE
        if not os.path.exists(path):
            return _fresh()

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None

        if data is None or not _is_valid(data):
            _backup_corrupt(path)
            return _fresh()

        data.setdefault("facts", {})
        data.setdefault("history", [])
        return data


def save_memory(memory: dict):
    with _LOCK:
        path = MEMORY_FILE
        folder = os.path.dirname(path)
        os.makedirs(folder, exist_ok=True)

        # Atomic write: temp file in the same folder, then os.replace.
        fd, tmp = tempfile.mkstemp(dir=folder, prefix=".memory-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise


# -------- CHAT HISTORY --------
def save_message(role: str, content: str):
    with _LOCK:
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
    with _LOCK:
        memory = load_memory()
        memory["facts"]["user_name"] = name.strip()
        save_memory(memory)


def get_user_name():
    memory = load_memory()
    return memory["facts"].get("user_name")
