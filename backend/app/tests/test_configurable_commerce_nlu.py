import json

from app.agents.intent_router import classify_intent
from app.agents.purchase import parse_cart_action
from app.services.business_rules import load_commerce_rules


def test_configured_purchase_phrase_routes_to_purchase_help(tmp_path, monkeypatch) -> None:
    rules_path = tmp_path / "commerce_rules.json"
    rules_path.write_text(
        json.dumps({"nlu": {"commands": {"add_to_cart": {"contains": ["安排进袋子"]}}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setenv("COMMERCE_RULES_PATH", str(rules_path))
    load_commerce_rules.cache_clear()
    try:
        result = classify_intent("这款先安排进袋子")
        assert result.intent == "purchase_help"
    finally:
        load_commerce_rules.cache_clear()


def test_configured_cart_view_phrase_controls_purchase_action(tmp_path, monkeypatch) -> None:
    rules_path = tmp_path / "commerce_rules.json"
    rules_path.write_text(
        json.dumps({"nlu": {"commands": {"view_cart": {"contains": ["看下袋子"]}}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setenv("COMMERCE_RULES_PATH", str(rules_path))
    load_commerce_rules.cache_clear()
    try:
        assert parse_cart_action("帮我看下袋子") == "view"
    finally:
        load_commerce_rules.cache_clear()
