from app.services.constraint_parser import parse_constraints, product_is_excluded


def test_large_screen_negative_constraint_excludes_large_screen_products() -> None:
    constraints = parse_constraints("有没有便宜一点的，最好拍照好、续航久，不要太大屏")

    assert {"kind": "exclude", "value": "大屏", "raw": "不要太大屏"} in constraints["exclusions"]
    assert product_is_excluded(
        title="小米 17 Max 大屏长续航高性能影像游戏5G智能手机",
        brand="小米",
        description="大屏长续航手机",
        exclusions=constraints["exclusions"],
    )
