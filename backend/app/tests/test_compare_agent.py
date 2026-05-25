from app.agents.compare import build_compare_answer
from app.agents.intent_router import classify_intent
from app.models.tables import Product


def test_difference_question_routes_to_compare() -> None:
    result = classify_intent("\u4ed6\u4eec\u4e24\u4e2a\u7684\u533a\u522b\u662f\uff1f")

    assert result.intent == "compare"


def test_tablet_difference_answer_uses_catalog_specs_and_docs() -> None:
    vivo = _product(
        "p_digital_019",
        "vivo Pad 6 Pro 12.1英寸高刷全面屏学习娱乐多任务办公平板电脑",
        "vivo",
        3299,
        3.6,
        1750,
        "12.1英寸高刷全面屏，学习模式，Wi-Fi6，支持OTG外接移动硬盘。",
        '{"sku_options":["8GB+256GB Wi-Fi 版","12GB+512GB 全网通5G版"],'
        '"price_range":{"min":3299,"max":4299},"review_summary":{"negative_review_count":0}}',
    )
    xiaomi = _product(
        "p_digital_011",
        "小米平板 8 Pro 12.1英寸高刷大屏影音娱乐学习办公平板电脑",
        "小米",
        3299,
        3.0,
        1050,
        "2.8K超清分辨率配合144Hz自适应刷新率，适配小米生态跨屏互联，仅支持Wi-Fi联网。",
        '{"sku_options":["8GB 256GB Wi-Fi版","12GB 512GB Wi-Fi版"],'
        '"price_range":{"min":3299,"max":3799},"review_summary":{"negative_review_count":1}}',
    )
    docs = {
        "p_digital_019": [
            {"text": "回答：vivo Pad 6 Pro最多支持4个应用窗口，学习模式可以降低蓝光，两个版本都支持OTG外接最大2TB移动硬盘。"}
        ],
        "p_digital_011": [
            {"text": "回答：小米平板8 Pro是2.8K超清分辨率和144Hz自适应高刷，支持小米手机跨屏互联，但没有插卡蜂窝版本。"}
        ],
    }

    answer = build_compare_answer([vivo, xiaomi], query="他们两个的区别是？", docs_by_product=docs)

    assert "主要区别" in answer
    assert "5G" in answer
    assert "Wi-Fi" in answer
    assert "2.8K" in answer
    assert "144Hz" in answer
    assert "跨屏互联" in answer
    assert "OTG" in answer
    assert "您可以优先看" in answer
    assert "你主要是在看你这次提到的重点" not in answer


def _product(
    product_id: str,
    title: str,
    brand: str,
    price: int,
    rating: float,
    sales: int,
    description: str,
    specs_json: str,
) -> Product:
    return Product(
        id=product_id,
        title=title,
        category="数码电子",
        brand=brand,
        price=price,
        description=description,
        specs_json=specs_json,
        rating=rating,
        sales=sales,
        stock=10,
        image_url="",
    )
