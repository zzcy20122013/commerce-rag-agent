"""Small, durable regression cases for project-roadshow shopping conversations."""

from __future__ import annotations


DEMO_REGRESSION_CASES: list[dict] = [
    {
        "case_id": "intent_001_tablet_budget",
        "query": "推荐 3500 以内学生记笔记平板",
        "expected_intent": "shopping_guide",
        "expected_constraints": {"category": "数码电子", "subcategory": "平板", "budget_max": 3500},
    },
    {
        "case_id": "intent_002_commute_shoes_budget",
        "query": "推荐 300 以内通勤鞋",
        "expected_intent": "shopping_guide",
        "expected_constraints": {"category": "服饰运动", "subcategory": "鞋", "budget_max": 300, "use_cases": ["通勤"]},
    },
    {
        "case_id": "intent_003_oil_control_base_budget",
        "query": "找 100 元以内控油粉饼",
        "expected_intent": "shopping_guide",
        "expected_constraints": {"category": "美妆护肤", "subcategory": "底妆", "budget_max": 100},
    },
    {
        "case_id": "intent_004_low_fat_breakfast",
        "query": "找 60 元内低脂早餐麦片",
        "expected_intent": "shopping_guide",
        "expected_constraints": {"category": "食品饮料", "subcategory": "早餐", "budget_max": 60},
    },
    {
        "case_id": "intent_005_earbuds_commute",
        "query": "想买一副通勤降噪耳机",
        "expected_intent": "shopping_guide",
        "expected_constraints": {"category": "数码电子", "subcategory": "耳机", "use_cases": ["通勤"]},
    },
    {
        "case_id": "intent_006_open_ended_skincare",
        "query": "我不知道怎么选护肤品，帮我看看买什么",
        "expected_intent": "decision_guide",
        "expected_constraints": {"category": "美妆护肤"},
    },
    {
        "case_id": "intent_007_open_ended_sunscreen",
        "query": "敏感肌想买防晒但不知道怎么选",
        "expected_intent": "decision_guide",
        "expected_constraints": {"category": "美妆护肤", "subcategory": "防晒"},
    },
    {
        "case_id": "intent_008_product_specs",
        "query": "这款平板的屏幕参数是多少",
        "expected_intent": "product_knowledge",
        "expected_constraints": {"category": "数码电子", "subcategory": "平板"},
    },
    {
        "case_id": "intent_009_product_ingredients",
        "query": "这款防晒成分是什么，敏感肌可以用吗",
        "expected_intent": "product_knowledge",
        "expected_constraints": {"category": "美妆护肤", "subcategory": "防晒"},
    },
    {
        "case_id": "intent_010_compare_two_products",
        "query": "这两个有什么区别",
        "expected_intent": "compare",
    },
    {
        "case_id": "intent_011_compare_named_brands",
        "query": "vivo 和小米哪个好",
        "expected_intent": "compare",
    },
    {
        "case_id": "intent_012_add_to_cart",
        "query": "把小米加入购物车",
        "expected_intent": "purchase_help",
    },
    {
        "case_id": "intent_013_add_quantity",
        "query": "把刚才那个杯面加入 100 件",
        "expected_intent": "purchase_help",
    },
    {
        "case_id": "intent_014_update_cart_quantity",
        "query": "第二个数量改成 10",
        "expected_intent": "purchase_help",
    },
    {
        "case_id": "intent_015_clear_cart",
        "query": "清空购物车",
        "expected_intent": "purchase_help",
    },
    {
        "case_id": "intent_016_view_cart",
        "query": "看看购物车里有什么",
        "expected_intent": "purchase_help",
    },
    {
        "case_id": "intent_017_order_list",
        "query": "我的订单在哪里",
        "expected_intent": "order_query",
    },
    {
        "case_id": "intent_018_refund_order",
        "query": "申请退款",
        "expected_intent": "order_query",
    },
    {
        "case_id": "intent_019_after_sales_policy",
        "query": "退货政策是什么",
        "expected_intent": "faq",
    },
    {
        "case_id": "intent_020_chitchat",
        "query": "你好呀",
        "expected_intent": "chitchat",
    },
    {
        "case_id": "multiturn_001_more_brands",
        "query": "有其他品牌吗",
        "expected_intent": "clarification",
        "expected_routed_intent": "shopping_guide",
        "memory": {
            "category": "数码电子",
            "subcategory": "平板",
            "budget_max": 3500,
            "last_product_ids": ["p_digital_019", "p_digital_011"],
        },
    },
    {
        "case_id": "multiturn_002_strict_budget",
        "query": "300 真不能超",
        "expected_intent": "shopping_guide",
        "expected_routed_intent": "shopping_guide",
        "expected_constraints": {"budget_max": 300, "strict_filter": True},
        "memory": {
            "category": "服饰运动",
            "subcategory": "鞋",
            "budget_max": 300,
            "last_product_ids": ["p_shoe_001", "p_shoe_002"],
        },
    },
    {
        "case_id": "multiturn_003_compare_last_two",
        "query": "它们两个区别是什么",
        "expected_intent": "compare",
        "expected_routed_intent": "compare",
        "memory": {"last_product_ids": ["p_digital_019", "p_digital_011"]},
    },
    {
        "case_id": "multiturn_004_continue_other_options",
        "query": "还有其他的吗",
        "expected_intent": "clarification",
        "expected_routed_intent": "shopping_guide",
        "memory": {
            "category": "美妆护肤",
            "subcategory": "防晒",
            "budget_max": 200,
            "last_product_ids": ["p_beauty_006", "p_beauty_007"],
        },
    },
    {
        "case_id": "multiturn_005_product_followup",
        "query": "它支持防水吗",
        "expected_intent": "product_knowledge",
        "expected_routed_intent": "product_knowledge",
        "memory": {"last_product_ids": ["p_digital_021"]},
    },
    {
        "case_id": "multiturn_006_exclude_previous_brand",
        "query": "不要刚才那个品牌",
        "expected_intent": "clarification",
        "expected_routed_intent": "shopping_guide",
        "memory": {
            "category": "服饰运动",
            "subcategory": "鞋",
            "budget_max": 300,
            "use_cases": ["通勤"],
            "last_product_ids": ["p_shoe_001", "p_shoe_002"],
        },
    },
    {
        "case_id": "multiturn_007_durability_preference",
        "query": "如果我更看重耐穿呢",
        "expected_intent": "shopping_guide",
        "expected_routed_intent": "shopping_guide",
        "memory": {
            "category": "服饰运动",
            "subcategory": "鞋",
            "budget_max": 300,
            "use_cases": ["通勤"],
            "last_product_ids": ["p_shoe_001", "p_shoe_002"],
        },
    },
]
