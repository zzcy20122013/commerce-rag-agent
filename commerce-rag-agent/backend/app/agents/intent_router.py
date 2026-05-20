import re

from app.llm.schemas import IntentResult, ShoppingConstraints


CATEGORY_KEYWORDS = {
    "数码电子": [
        "数码",
        "电子",
        "平板",
        "pad",
        "tablet",
        "耳机",
        "蓝牙耳机",
        "headphone",
        "earbuds",
        "键盘",
        "充电宝",
        "智能手表",
        "显示器",
        "路由器",
        "相机",
        "电纸书",
    ],
    "服饰运动": [
        "服饰",
        "运动",
        "鞋",
        "跑鞋",
        "板鞋",
        "通勤鞋",
        "shoe",
        "sneaker",
        "背包",
        "双肩包",
        "电脑包",
        "bag",
        "backpack",
        "卫衣",
        "冲锋衣",
        "瑜伽裤",
        "羽绒服",
        "外套",
        "跑步",
        "健身",
    ],
    "美妆护肤": [
        "美妆",
        "护肤",
        "精华",
        "敏感肌",
        "修护",
        "维稳",
        "保湿",
        "面霜",
        "防晒",
        "爽肤水",
        "粉底",
        "唇釉",
        "眼霜",
        "洁面",
        "卸妆",
    ],
    "食品饮料": ["食品", "饮料", "零食", "咖啡", "酸奶", "麦片", "牛奶", "茶", "代餐", "早餐", "低脂"],
}
USE_CASE_KEYWORDS = {
    "记笔记": ["记笔记", "手写笔", "笔记", "notes", "note"],
    "网课": ["网课", "上课", "学习", "online class", "class"],
    "通勤": ["通勤", "commute"],
    "送礼": ["送礼", "礼物", "女朋友", "男朋友", "gift"],
    "敏感肌护理": ["敏感肌", "易敏肌", "舒缓", "泛红"],
    "修护维稳": ["修护", "维稳", "屏障", "强韧"],
    "保湿补水": ["保湿", "补水", "干皮", "干燥"],
    "抗初老": ["抗初老", "淡纹", "紧致", "抗皱"],
    "防晒": ["防晒", "户外", "防水防汗"],
    "控油": ["控油", "油皮", "油痘肌"],
    "低脂早餐": ["低脂", "早餐", "代餐", "轻食"],
}
PRODUCT_ID_PATTERN = re.compile(r"\bp\d{3}\b", re.IGNORECASE)


def classify_intent(text: str) -> IntentResult:
    normalized = text.lower()
    constraints = extract_shopping_constraints(text)

    if _contains_any(normalized, ["怎么购买", "如何购买", "怎么买", "购买流程", "怎么下单", "如何下单", "立即购买", "加入购物车", "checkout", "buy now"]):
        return IntentResult(intent="purchase_help", confidence=0.9, constraints=constraints)

    if _contains_any(normalized, ["订单", "物流", "快递", "到哪", "发货", "退货进度", "order", "shipping"]):
        return IntentResult(intent="order_query", confidence=0.9, constraints=constraints)

    if _contains_any(normalized, ["哪个好", "对比", "比较", "差别", "区别", "compare", "vs", "versus"]):
        return IntentResult(intent="compare", confidence=0.88, constraints=constraints)

    if _contains_any(normalized, ["防水", "参数", "续航", "材质", "重量", "屏幕", "降噪", "容量", "详情", "支持", "waterproof", "spec"]):
        return IntentResult(intent="product_knowledge", confidence=0.84, constraints=constraints)

    if _contains_any(normalized, ["退货政策", "售后", "保修", "发票", "faq", "policy"]):
        return IntentResult(intent="faq", confidence=0.82, constraints=constraints)

    if constraints.category or _contains_any(
        normalized,
        [
            "推荐",
            "预算",
            "以内",
            "以下",
            "适合",
            "更轻",
            "轻一点",
            "便宜",
            "换个",
            "找一款",
            "想买",
            "recommend",
            "under",
            "budget",
        ],
    ):
        confidence = 0.82 if constraints.category or constraints.budget_max else 0.66
        return IntentResult(intent="shopping_guide", confidence=confidence, constraints=constraints)

    if _contains_any(normalized, ["这两个", "这个", "有没有", "换一个", "更轻", "便宜点"]):
        return IntentResult(intent="clarification", confidence=0.55, constraints=constraints)

    return IntentResult(intent="chitchat", confidence=0.6, constraints=constraints)


def extract_shopping_constraints(text: str) -> ShoppingConstraints:
    budget = _extract_budget(text)
    return ShoppingConstraints(
        category=_extract_category(text),
        budget_max=budget,
        use_cases=_extract_use_cases(text),
        audience=_extract_audience(text),
        preferences=_extract_preferences(text, budget),
        product_ids=_extract_product_ids(text),
    )


def _extract_budget(text: str) -> int | None:
    match = re.search(r"(?:预算\s*)?(\d{2,6})\s*(?:元|块|以内|以下|under)?", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_category(text: str) -> str | None:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return None


def _extract_product_ids(text: str) -> list[str]:
    return [match.upper().replace("P", "p") for match in PRODUCT_ID_PATTERN.findall(text)]


def _extract_use_cases(text: str) -> list[str]:
    lowered = text.lower()
    return [
        use_case
        for use_case, keywords in USE_CASE_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]


def _extract_audience(text: str) -> str | None:
    if _contains_any(text, ["学生党", "学生", "上学"]):
        return "学生"
    if _contains_any(text, ["女朋友", "女生", "女友"]):
        return "女性送礼"
    if _contains_any(text, ["上班", "通勤", "职场"]):
        return "通勤人群"
    return None


def _extract_preferences(text: str, budget: int | None) -> list[str]:
    lowered = text.lower()
    preferences = []
    if _contains_any(lowered, ["性价比", "便宜", "划算", "budget"]) or budget is not None:
        preferences.append("性价比")
    if _contains_any(lowered, ["轻", "轻便", "便携", "portable"]):
        preferences.append("轻便")
    if _contains_any(lowered, ["舒适", "久走", "护眼"]):
        preferences.append("舒适")
    if _contains_any(lowered, ["敏感肌", "易敏肌", "温和", "无刺激"]):
        preferences.append("敏感肌友好")
    if _contains_any(lowered, ["修护", "维稳", "屏障"]):
        preferences.append("修护维稳")
    if _contains_any(lowered, ["保湿", "补水"]):
        preferences.append("保湿")
    if _contains_any(lowered, ["抗初老", "抗老", "淡纹", "紧致"]):
        preferences.append("抗初老")
    if _contains_any(lowered, ["低脂", "低糖", "代餐"]):
        preferences.append("低负担")
    return preferences


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
