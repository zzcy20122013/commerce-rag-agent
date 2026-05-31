import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "commerce_rules.json"


@lru_cache
def load_commerce_rules() -> dict[str, Any]:
    path = Path(os.getenv("COMMERCE_RULES_PATH") or DEFAULT_RULES_PATH)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as source:
        payload = json.load(source)
    return payload if isinstance(payload, dict) else {}


def rule_section(*keys: str) -> Any:
    value: Any = load_commerce_rules()
    for key in keys:
        if not isinstance(value, dict):
            return {}
        value = value.get(key, {})
    return value


def rule_list(*keys: str) -> list[Any]:
    value = rule_section(*keys)
    return value if isinstance(value, list) else []
