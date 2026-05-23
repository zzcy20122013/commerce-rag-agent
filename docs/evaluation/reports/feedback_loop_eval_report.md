# Feedback Loop Evaluation Report

## Metrics

- feedback_total: 5
- feedback_positive_count: 2
- feedback_negative_count: 3
- feedback_positive_rate: 0.4
- feedback_negative_rate: 0.6
- feedback_negative_reason_coverage: 1.0
- reason_不相关: 1
- reason_太贵: 1
- reason_解释不清: 1

## Failures

- `feedback_eval_fb_002` query=帮我推荐 300 以内通勤鞋 expected=太贵 actual=这双鞋脚感不错，但价格明显超出你的 300 元预算。
- `feedback_eval_fb_003` query=找 100 元以内控油粉饼 expected=不相关 actual=我给你推荐一款精华，修护维稳比较好。
- `feedback_eval_fb_004` query=这两款精华哪个更适合敏感肌？ expected=解释不清 actual=两款都还可以，建议你自己看看。
