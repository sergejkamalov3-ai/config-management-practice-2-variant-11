"""Чтение и проверка параметров YAML."""
import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml

PART = r"[A-Za-z0-9_+-]+(?:[.][A-Za-z0-9_+-]+)*"
FIELDS = "package repository test_mode version output max_depth".split()


def load(path):
    """Проверить шесть полей и разрешить относительные пути."""
    path = Path(path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict) or set(cfg) != set(FIELDS):
        raise ValueError("Ожидаются поля: " + ", ".join(FIELDS))
    if type(cfg["test_mode"]) is not bool:
        raise ValueError("test_mode: требуется true или false")
    pattern = "[A-Z]+" if cfg["test_mode"] else f"{PART}:{PART}"
    for key, form in [("package", pattern), ("version", PART)]:
        value = cfg[key]
        if not isinstance(value, str) or not re.fullmatch(form, value):
            raise ValueError(f"{key}: недопустимое значение {value!r}")
    depth = cfg["max_depth"]
    if type(depth) is not int or depth < 0:
        raise ValueError("max_depth: требуется целое число от нуля")
    for key in ("repository", "output"):
        if not isinstance(cfg[key], str) or not cfg[key].strip():
            raise ValueError(f"{key}: требуется непустая строка")
    out = path.parent / cfg["output"]
    if out.suffix.lower() != ".png" or out.is_dir():
        raise ValueError("output: требуется путь к файлу PNG")
    cfg["output"] = str(out.resolve())
    repo = cfg["repository"]
    if cfg["test_mode"]:
        file = path.parent / repo
        if not file.is_file():
            raise ValueError(f"repository: файл не найден: {file}")
        cfg["repository"] = str(file.resolve())
    else:
        validate_url(repo)
    return cfg


def validate_url(value):
    """Проверить адрес и порт до начала сетевых запросов."""
    try:
        parts = urlsplit(value)
        port = parts.port
        valid = (parts.scheme in {"http", "https"} and parts.hostname
                 and not parts.query and not parts.fragment
                 and not parts.username and not parts.password
                 and not any(c.isspace() or ord(c) < 32 for c in value)
                 and not parts.netloc.endswith(":")
                 and (port is None or port > 0))
    except ValueError as error:
        raise ValueError("repository: некорректный URL или порт") from error
    if not valid:
        raise ValueError("repository: требуется базовый URL HTTP(S)")
