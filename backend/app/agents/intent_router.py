import re

from app.llm.schemas import IntentResult, ShoppingConstraints
from app.services.taxonomy import extract_taxonomy_constraints


PRODUCT_ID_PATTERN = re.compile(r"\bp(?:_\w+)?_\d{3}\b|\bp\d{3}\b", re.IGNORECASE)


MORE_OPTIONS_KEYWORDS = [
    "还有吗",
    "其他的",
    "其他品牌",
    "有其他品牌",
    "别的吗",
    "别的品牌",
    "换一批",
    "再推荐",
    "再找",
    "有没有别的",
]

PURCHASE_KEYWORDS = [
    "怎么购买",
    "如何购买",
    "怎么买",
    "购买流程",
    "怎么下单",
    "如何下单",
    "立即购买",
    "加入购物车",
    "购物车",
    "购物袋",
    "加购",
    "加入",
    "删掉",
    "删除第",
    "移除第",
    "数量改",
    "改成",
    "checkout",
    "buy now",
]

ORDER_ACTION_KEYWORDS = [
    "订单",
    "我的订单",
    "物流",
    "快递",
    "到哪",
    "发货",
    "确认收货",
    "收货",
    "退款",
    "退货进度",
    "申请售后",
    "申请退货",
    "取消订单",
    "删除订单",
    "支付",
    "付款",
    "order",
    "shipping",
]

COMPARE_KEYWORDS = ["哪个好", "哪个", "哪款", "哪一个", "对比", "比较", "差别", "区别", "compare", "vs", "versus"]

PRODUCT_KNOWLEDGE_KEYWORDS = [
    "防水",
    "参数",
    "续航",
    "材质",
    "重量",
    "屏幕",
    "降噪",
    "容量",
    "详情",
    "支持",
    "成分",
    "功效",
    "怎么用",
    "如何使用",
    "用法",
    "注意事项",
    "适合敏感肌",
    "敏感肌可以",
    "waterproof",
    "spec",
]

SHOPPING_GUIDE_KEYWORDS = [
    "推荐",
    "预算",
    "以内",
    "以下",
    "适合",
    "更轻",
    "轻一点",
    "便宜",
    "换个",
    "耐穿",
    "耐用",
    "找一款",
    "想买",
    "recommend",
    "under",
    "budget",
]


def classify_intent(text: str) -> IntentResult:
    normalized = text.lower()
    constraints = extract_shopping_constraints(text)

    if _is_open_ended_purchase_question(normalized, constraints):
        return IntentResult(intent="decision_guide", confidence=0.86, constraints=constraints)

    if _contains_any(normalized, MORE_OPTIONS_KEYWORDS):
        return IntentResult(intent="clarification", confidence=0.72, constraints=constraints)

    if _contains_any(
        normalized,
        ["计算机专业", "编程", "代码", "开发", "软件", "3d游戏", "游戏", "打游戏", "显卡", "独显", "专业"],
    ):
        return IntentResult(intent="clarification", confidence=0.72, constraints=constraints)

    if _is_faq_request(normalized):
        return IntentResult(intent="faq", confidence=0.82, constraints=constraints)

    if _contains_any(normalized, ORDER_ACTION_KEYWORDS):
        return IntentResult(intent="order_query", confidence=0.9, constraints=constraints)

    if _contains_any(normalized, PURCHASE_KEYWORDS):
        return IntentResult(intent="purchase_help", confidence=0.9, constraints=constraints)

    if _contains_any(normalized, COMPARE_KEYWORDS):
        return IntentResult(intent="compare", confidence=0.88, constraints=constraints)

    if constraints.product_ids or (
        _contains_any(normalized, PRODUCT_KNOWLEDGE_KEYWORDS)
        and not _contains_any(
            normalized,
            ["推荐", "帮我选", "预算", "以内", "以下", "想买", "找一款", "找个", "买一", "recommend", "budget"],
        )
    ):
        return IntentResult(intent="product_knowledge", confidence=0.84, constraints=constraints)

    if constraints.category or constraints.budget_max or _contains_any(normalized, SHOPPING_GUIDE_KEYWORDS):
        confidence = 0.82 if constraints.category or constraints.budget_max else 0.66
        return IntentResult(intent="shopping_guide", confidence=confidence, constraints=constraints)

    if _contains_any(
        normalized,
        [
            "这两个",
            "这个",
            "有没有",
            "换一个",
            "更轻",
            "便宜点",
            "更看重",
            "耐穿",
            "耐用",
            "不要刚才",
            "刚才那个品牌",
            "不能超",
            "别超",
            "不超",
            "不要超",
            "卡死",
        ],
    ):
        return IntentResult(intent="clarification", confidence=0.55, constraints=constraints)

    return IntentResult(intent="chitchat", confidence=0.6, constraints=constraints)


def extract_shopping_constraints(text: str) -> ShoppingConstraints:
    budget = _extract_budget(text)
    taxonomy = extract_taxonomy_constraints(text, budget=budget)
    return ShoppingConstraints(
        category=taxonomy.category,
        subcategory=taxonomy.subcategory,
        budget_max=budget,
        use_cases=taxonomy.use_cases,
        audience=_extract_audience(text),
        preferences=taxonomy.preferences,
        product_ids=_extract_product_ids(text),
        strict_filter=taxonomy.strict_filter,
    )


def _extract_budget(text: str) -> int | None:
    cleaned = PRODUCT_ID_PATTERN.sub(" ", text)
    patterns = [
        r"(\d{2,6})\s*(?:元|块)?\s*(?:真)?\s*(?:不能超|别超|不超|不要超|以内必须|必须以内|卡死)",
        r"(?:预算|价格|价位)?\s*(\d{2,6})\s*(?:元|块)\s*(?:以内|以下|内)?",
        r"(?:预算|价格|价位)\s*(?:<=|小于|不超过|低于)?\s*(\d{2,6})",
        r"(\d{2,6})\s*(?:以内|以下|under)",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_product_ids(text: str) -> list[str]:
    return [match.lower() for match in PRODUCT_ID_PATTERN.findall(text)]


def _extract_audience(text: str) -> str | None:
    if _contains_any(text, ["学生党", "学生", "上学"]):
        return "学生"
    if _contains_any(text, ["大学", "大学生", "准大学生"]):
        return "学生"
    if _contains_any(text, ["女朋友", "女生", "女友"]):
        return "女性送礼"
    if _contains_any(text, ["上班", "通勤", "职场"]):
        return "通勤人群"
    return None


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_faq_request(text: str) -> bool:
    return _contains_any(text, ["退货政策", "售后政策", "保修", "发票", "faq", "policy"])


def _is_open_ended_purchase_question(text: str, constraints: ShoppingConstraints) -> bool:
    if not constraints.category and not constraints.subcategory:
        return False
    return _contains_any(
        text,
        [
            "不知道买什么",
            "不知道要买什么",
            "不知道买哪",
            "不知道怎么选",
            "买什么样",
            "怎么选",
            "选购",
            "有推荐吗",
            "帮我看看买什么",
        ],
    ) and not constraints.budget_max
