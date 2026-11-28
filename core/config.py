"""Environment settings loaded once at import."""

import logging
import math
import os
from pathlib import Path
from urllib.parse import urlsplit


_LOGGER = logging.getLogger(__name__)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(name, default, parse):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return parse(value.strip())
    except (ValueError, OSError, OverflowError):
        _LOGGER.warning("Invalid value for %s; using the default", name)
        return default


def _model(value):
    if not value or any(char.isspace() for char in value):
        raise ValueError
    return value


def _base_url(value):
    url = urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username is not None
        or "?" in value
        or "#" in value
        or any(char.isspace() for char in value)
        or url.port == 0
    ):
        raise ValueError
    return value.rstrip("/")


def _positive(number):
    if number <= 0:
        raise ValueError
    return number


def _timeout(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError
    return _positive(number)


def _temperature(value):
    number = float(value)
    if not 0 <= number <= 2:
        raise ValueError
    return number


def _boolean(value):
    value = value.lower()
    if value in {"1", "true", "yes"}:
        return True
    if value in {"0", "false", "no"}:
        return False
    raise ValueError


def _data_dir(value):
    if not value:
        raise ValueError
    path = _PROJECT_ROOT / value
    if not path.is_absolute():
        raise ValueError
    return os.path.normpath(path)


MODEL = _read("NEURAXAI_MODEL", "phi3:mini", _model)
OLLAMA_URL = _read("NEURAXAI_OLLAMA_URL", "http://localhost:11434", _base_url)
CONNECT_TIMEOUT = _read("NEURAXAI_CONNECT_TIMEOUT", 3.0, _timeout)
READ_TIMEOUT = _read("NEURAXAI_READ_TIMEOUT", 120.0, _timeout)
TEMPERATURE = _read("NEURAXAI_TEMPERATURE", 0.7, _temperature)
MAX_MESSAGE_CHARS = _read("NEURAXAI_MAX_MESSAGE_CHARS", 4000, lambda value: _positive(int(value)))
DEBUG = _read("NEURAXAI_DEBUG", False, _boolean)
DATA_DIR = _read("NEURAXAI_DATA_DIR", str(_PROJECT_ROOT / "data"), _data_dir)
