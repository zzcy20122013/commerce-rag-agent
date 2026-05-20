import { useState } from "react";
import { ShoppingBag, Star } from "lucide-react";
import { absoluteUrl } from "../api/config";
import type { ProductCard } from "../api/types";

type ProductCardsProps = {
  cards: ProductCard[];
};

export function ProductCards({ cards }: ProductCardsProps) {
  if (!cards.length) return null;
  return (
    <div className="product-strip">
      {cards.map((card) => (
        <article className="product-card" key={card.product_id}>
          <ProductImage imageUrl={card.image_url} title={card.title} />
          <div className="product-body">
            <div className="product-title">{card.title}</div>
            <div className="product-subtitle">{card.subtitle}</div>
            <div className="product-meta">
              <strong>¥ {card.price}</strong>
              <span>
                <Star size={14} /> {card.rating}
              </span>
              <span>{card.sales} 销量</span>
            </div>
            <div className="reason-list">
              {card.reasons.map((reason) => (
                <span key={reason}>{reason}</span>
              ))}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function ProductImage({ imageUrl, title }: { imageUrl: string; title: string }) {
  const [failed, setFailed] = useState(false);
  if (!imageUrl || failed) {
    return (
      <div className="product-image placeholder" aria-label={title}>
        <ShoppingBag size={26} />
      </div>
    );
  }
  return (
    <div className="product-image">
      <img src={absoluteUrl(imageUrl)} alt="" aria-label={title} onError={() => setFailed(true)} />
    </div>
  );
}
