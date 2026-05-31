from app.services.business_rules import rule_dict


SLOT_LABELS = {
    "budget_max": "预算",
    "use_cases": "使用场景",
    "preferences": "偏好/不能接受点",
    "audience": "使用人群",
    "subcategory": "子品类",
}


CATEGORY_SOPS = [
    {
        "sop_name": "运动鞋导购SOP",
        "keywords": ["鞋", "跑鞋", "板鞋", "通勤鞋"],
        "required_slots": ["budget_max", "use_cases", "preferences"],
        "evidence_priorities": ["脚感", "缓震", "耐穿", "尺码", "通勤/跑步场景"],
    },
    {
        "sop_name": "平板电脑导购SOP",
        "keywords": ["平板", "pad", "tablet"],
        "required_slots": ["budget_max", "use_cases", "preferences"],
        "evidence_priorities": ["屏幕", "续航", "存储", "手写笔/键盘", "学习/办公场景"],
    },
    {
        "sop_name": "护肤品导购SOP",
        "keywords": ["护肤", "精华", "面霜", "防晒", "乳液"],
        "required_slots": ["budget_max", "audience", "preferences"],
        "evidence_priorities": ["肤质", "敏感肌风险", "功效成分", "刺激性评价"],
    },
    {
        "sop_name": "食品饮料导购SOP",
        "keywords": ["咖啡", "麦片", "酸奶", "零食", "食品", "饮料"],
        "required_slots": ["budget_max", "use_cases", "preferences"],
        "evidence_priorities": ["口味", "糖脂含量", "冲泡/食用场景", "规格单价"],
    },
]


QUERY_SLOT_HINTS = {
    "use_cases": [
        "通勤",
        "跑步",
        "健身",
        "户外",
        "网课",
        "记笔记",
        "办公",
        "早餐",
        "送礼",
    ],
    "preferences": [
        "耐穿",
        "轻便",
        "低糖",
        "敏感肌",
        "保湿",
        "修护",
        "国产",
        "性价比",
        "便宜",
    ],
    "audience": ["男生", "女生", "学生", "老人", "孩子", "敏感肌"],
}


def build_category_sop_context(memory: dict, query: str = "") -> dict:
    sop = _match_sop(memory, query)
    missing_slots = [
        slot
        for slot in sop["required_slots"]
        if not _slot_has_value(slot, memory, query)
    ]
    return {
        "sop_name": sop["sop_name"],
        "required_slots": sop["required_slots"],
        "missing_slots": missing_slots,
        "missing_slot_labels": [SLOT_LABELS.get(slot, slot) for slot in missing_slots],
        "evidence_priorities": sop["evidence_priorities"],
    }


def _match_sop(memory: dict, query: str) -> dict:
    rule_sop = _rule_sop(memory)
    if rule_sop:
        return rule_sop
    context = " ".join(
        str(value)
        for value in [
            memory.get("category", ""),
            memory.get("subcategory", ""),
            query,
        ]
        if value
    ).lower()
    for sop in CATEGORY_SOPS:
        if any(keyword.lower() in context for keyword in sop["keywords"]):
            return sop
    return {
        "sop_name": "通用导购SOP",
        "required_slots": ["budget_max", "use_cases", "preferences"],
        "evidence_priorities": ["价格", "销量", "评分", "商品规格", "用户评价"],
    }


def _rule_sop(memory: dict) -> dict | None:
    subcategory = str(memory.get("subcategory") or "").strip()
    if not subcategory:
        return None
    payload = rule_dict("guide_sops", "subcategories").get(subcategory)
    if not isinstance(payload, dict):
        return None
    required_slots = _flatten_required_slots(payload.get("required_any"))
    evidence_focus = [str(item) for item in payload.get("evidence_focus") or [] if str(item).strip()]
    return {
        "sop_name": str(payload.get("sop_name") or f"{subcategory}导购SOP"),
        "required_slots": required_slots or ["budget_max", "use_cases", "preferences"],
        "evidence_priorities": evidence_focus or ["价格", "销量", "评分", "商品规格", "用户评价"],
    }


def _flatten_required_slots(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    slots: list[str] = []
    for group in value:
        if isinstance(group, list):
            slots.extend(str(item) for item in group if str(item))
        elif str(group):
            slots.append(str(group))
    return list(dict.fromkeys(slots))


def _slot_has_value(slot: str, memory: dict, query: str) -> bool:
    value = memory.get(slot)
    if value not in (None, "", [], {}, False):
        return True
    return any(keyword.lower() in query.lower() for keyword in QUERY_SLOT_HINTS.get(slot, []))
