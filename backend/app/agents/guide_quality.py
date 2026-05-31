from app.agents.category_sop import build_category_sop_context


def evaluate_guide_quality(
    *,
    memory: dict,
    cards: list[dict],
    retrieval_trace: dict,
    query: str,
) -> dict:
    category_sop = build_category_sop_context(memory, query)
    quality_flags = _quality_flags(cards, retrieval_trace, category_sop)
    return {
        "category_sop": category_sop,
        "missing_slots": category_sop["missing_slots"],
        "evidence_priorities": category_sop["evidence_priorities"],
        "quality_flags": quality_flags,
        "needs_clarification": _needs_clarification(category_sop, quality_flags),
        "evidence_score": _evidence_score(cards, retrieval_trace),
    }


def _quality_flags(cards: list[dict], retrieval_trace: dict, category_sop: dict) -> list[str]:
    flags: list[str] = []
    if retrieval_trace.get("low_confidence"):
        flags.append("low_confidence_retrieval")
    if not cards:
        flags.append("no_candidate_cards")
    if category_sop["missing_slots"]:
        flags.append("missing_key_slots")
    if cards and not _has_non_basic_evidence(cards):
        flags.append("thin_product_evidence")
    return flags


def _needs_clarification(category_sop: dict, quality_flags: list[str]) -> bool:
    if "no_candidate_cards" in quality_flags and category_sop["missing_slots"]:
        return True
    return "low_confidence_retrieval" in quality_flags and len(category_sop["missing_slots"]) >= 2


def _evidence_score(cards: list[dict], retrieval_trace: dict) -> float:
    if not cards:
        return 0.0
    score = 0.35
    if _has_non_basic_evidence(cards):
        score += 0.3
    if any(card.get("review_insight") for card in cards):
        score += 0.15
    if not retrieval_trace.get("low_confidence"):
        score += 0.2
    return round(min(score, 1.0), 2)


def _has_non_basic_evidence(cards: list[dict]) -> bool:
    for card in cards:
        for item in card.get("evidence", []):
            source = str(item.get("source", ""))
            if source and source != "价格/销量/评分":
                return True
    return False
