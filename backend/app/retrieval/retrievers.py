from sqlalchemy.orm import Session

from app.retrieval.text_index import TextIndex


def retrieve_product_text(db: Session, query: str, *, limit: int = 5, chroma_path: str | None = None) -> list[dict]:
    index = TextIndex(chroma_path=chroma_path)
    index.index_products(db)
    return index.search_products(query, limit=limit)


def retrieve_faq(query: str, *, limit: int = 3, chroma_path: str | None = None) -> list[dict]:
    index = TextIndex(chroma_path=chroma_path)
    index.index_faqs()
    return index.search_faq(query, limit=limit)
