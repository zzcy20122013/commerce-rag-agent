import type { CSSProperties, ReactNode } from "react";
import { CheckCircle2, Trophy } from "lucide-react";
import type { ComparisonPayload } from "../api/types";

type ComparisonTableProps = {
  comparison?: ComparisonPayload | null;
};

export function ComparisonTable({ comparison }: ComparisonTableProps) {
  if (!comparison || comparison.items.length === 0) return null;
  const winner = comparison.items.find((item) => item.product_id === comparison.winner_product_id);

  const gridStyle = {
    "--comparison-columns": comparison.items.length,
  } as CSSProperties;

  return (
    <details className="comparison-panel" aria-label="商品对比">
      <summary className="comparison-header">
        <div>
          <span className="comparison-kicker">可展开查看</span>
          <strong>{comparison.title || "商品对比细节"}</strong>
        </div>
        {winner && (
          <span className="winner-pill">
            <Trophy size={14} /> 更建议 {winner.title}
          </span>
        )}
      </summary>

      {comparison.winner_reason && <p className="comparison-reason">{comparison.winner_reason}</p>}

      <div className="comparison-scroll" style={gridStyle}>
        <div className="comparison-row comparison-row-head">
          <div className="comparison-label">维度</div>
          {comparison.items.map((item) => (
            <div className="comparison-product-title" key={item.product_id}>
              {item.is_winner && <CheckCircle2 size={15} />}
              <span>{item.title}</span>
            </div>
          ))}
        </div>
        <ComparisonRow label="价格" values={comparison.items.map((item) => `￥${item.price}`)} />
        <ComparisonRow label="评分 / 销量" values={comparison.items.map((item) => `${item.rating} / ${item.sales}`)} />
        <ComparisonRow
          label="需求匹配"
          values={comparison.items.map((item) =>
            item.matched_keywords.length > 0 ? item.matched_keywords.join("、") : "未命中特定关键词"
          )}
        />
        <ComparisonListRow label="优势" values={comparison.items.map((item) => item.pros)} />
        <ComparisonListRow label="注意点" values={comparison.items.map((item) => item.cons)} />
        <ComparisonRow label="适用建议" values={comparison.items.map((item) => item.best_for || "结合预算和偏好选择")} />
        <ComparisonRow label="证据" values={comparison.items.map((item) => item.evidence || "来自商品结构化信息")} />
      </div>
    </details>
  );
}

function ComparisonRow({ label, values }: { label: string; values: ReactNode[] }) {
  return (
    <div className="comparison-row">
      <div className="comparison-label">{label}</div>
      {values.map((value, index) => (
        <div className="comparison-cell" key={`${label}-${index}`}>
          {value}
        </div>
      ))}
    </div>
  );
}

function ComparisonListRow({ label, values }: { label: string; values: string[][] }) {
  return (
    <ComparisonRow
      label={label}
      values={values.map((items, index) => (
        <ul className="comparison-list" key={`${label}-${index}`}>
          {(items.length > 0 ? items : ["暂无明显信息"]).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ))}
    />
  );
}
