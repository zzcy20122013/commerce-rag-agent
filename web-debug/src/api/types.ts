export type ProductCard = {
  product_id: string;
  title: string;
  subtitle: string;
  price: number;
  original_price: number;
  image_url: string;
  rating: number;
  sales: number;
  stock_status: string;
  reasons: string[];
  score: number;
};

export type ChatMessageEvent = {
  content: string;
  message_id?: string;
  session_id?: string;
  memory?: Record<string, unknown>;
};

export type ComparisonItem = {
  product_id: string;
  title: string;
  price: number;
  rating: number;
  sales: number;
  stock_status: string;
  matched_keywords: string[];
  pros: string[];
  cons: string[];
  best_for: string;
  evidence: string;
  is_winner: boolean;
};

export type ComparisonPayload = {
  type: "comparison";
  title: string;
  dimensions: string[];
  winner_product_id: string;
  winner_reason: string;
  items: ComparisonItem[];
};

export type DebugEvent =
  | { event: "message"; data: ChatMessageEvent; raw: string }
  | { event: "trace"; data: unknown; raw: string }
  | { event: "product_cards"; data: ProductCard[]; raw: string }
  | { event: "comparison"; data: ComparisonPayload; raw: string }
  | { event: "done"; data: unknown; raw: string }
  | { event: "error"; data: unknown; raw: string };

export type UploadResult = {
  upload_id: string;
  local_path: string;
  preview_url: string;
};

export type IngestResult = {
  document_id: string;
  chunks: number;
};
