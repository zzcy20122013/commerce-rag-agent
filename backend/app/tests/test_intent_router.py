import pytest

from app.agents.graph import router_node
from app.agents.intent_router import classify_intent


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("打开购物车", "purchase_help"),
        ("清空购物车", "purchase_help"),
        ("把小米加入购物车", "purchase_help"),
        ("我的订单", "order_query"),
        ("确认收货", "order_query"),
        ("申请退款", "order_query"),
        ("支付这个订单", "order_query"),
        ("这两个有什么区别", "compare"),
        ("vivo 和小米哪个好", "compare"),
        ("这款支持 5G 吗", "product_knowledge"),
        ("它的屏幕参数是多少", "product_knowledge"),
        ("还有其他品牌吗", "clarification"),
        ("300 真不能超", "shopping_guide"),
        ("有没有便宜一点的，最好拍照好、续航久，不要太大屏", "shopping_guide"),
        ("不要太贵，也别太刺激，优先国货", "shopping_guide"),
    ],
)
def test_classify_intent_for_demo_phrases(query: str, expected: str) -> None:
    assert classify_intent(query).intent == expected


def test_router_keeps_more_options_followup_in_shopping_context() -> None:
    result = router_node(
        {
            "query": "有其他品牌吗",
            "memory": {
                "last_product_ids": ["p_digital_019", "p_digital_011"],
                "category": "数码电子",
                "subcategory": "平板",
                "budget_max": 3500,
            },
            "trace": [],
        }
    )

    assert result["intent"] == "shopping_guide"


def test_router_treats_difference_followup_as_compare() -> None:
    result = router_node(
        {
            "query": "它们两个区别是什么",
            "memory": {"last_product_ids": ["p_digital_019", "p_digital_011"]},
            "trace": [],
        }
    )

    assert result["intent"] == "compare"


def test_router_keeps_beauty_refinement_followup_in_shopping_context() -> None:
    result = router_node(
        {
            "query": "不要太贵，也别太刺激，优先国货",
            "memory": {
                "category": "美妆护肤",
                "subcategory": "精华",
                "budget_max": 300,
                "preferences": ["敏感肌友好", "保湿", "修护维稳"],
                "last_product_ids": ["p_beauty_001"],
            },
            "trace": [],
        }
    )

    assert result["intent"] == "shopping_guide"
