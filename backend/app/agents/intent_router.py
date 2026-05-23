import re

from app.llm.schemas import IntentResult, ShoppingConstraints
from app.services.taxonomy import extract_taxonomy_constraints


PRODUCT_ID_PATTERN = re.compile(r"\bp(?:_\w+)?_\d{3}\b|\bp\d{3}\b", re.IGNORECASE)


def classify_intent(text: str) -> IntentResult:
    normalized = text.lower()
    constraints = extract_shopping_constraints(text)

    if _is_open_ended_purchase_question(normalized, constraints):
        return IntentResult(intent="decision_guide", confidence=0.86, constraints=constraints)

    if _contains_any(normalized, ["还有吗", "其他的", "别的吗", "换一批", "再推荐", "再找", "有没有别的"]):
        return IntentResult(intent="clarification", confidence=0.72, constraints=constraints)

    if _contains_any(
        normalized,
        ["计算机专业", "编程", "代码", "开发", "软件", "3d游戏", "游戏", "打游戏", "显卡", "独显", "专业"],
    ):
        return IntentResult(intent="clarification", confidence=0.72, constraints=constraints)

    if _contains_any(
        normalized,
        [
            "怎么购买",
            "如何购买",
            "怎么买",
            "购买流程",
            "怎么下单",
            "如何下单",
            "立即购买",
            "加入购物车",
            "购物车",
            "加购",
            "加入",
            "删掉",
            "删除第",
            "移除第",
            "数量改",
            "改成",
            "checkout",
            "buy now",
        ],
    ):
        return IntentResult(intent="purchase_help", confidence=0.9, constraints=constraints)

    if _contains_any(normalized, ["订单", "物流", "快递", "到哪", "发货", "退货进度", "order", "shipping"]):
        return IntentResult(intent="order_query", confidence=0.9, constraints=constraints)

    if _contains_any(normalized, ["哪个好", "哪个", "哪款", "哪一个", "对比", "比较", "差别", "区别", "compare", "vs", "versus"]):
        return IntentResult(intent="compare", confidence=0.88, constraints=constraints)

    if constraints.product_ids or (
        _contains_any(
            normalized,
            [
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
            ],
        )
        and not _contains_any(normalized, ["推荐", "帮我选", "预算", "以内", "以下", "recommend", "budget"])
    ):
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
