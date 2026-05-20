from app.llm.generation import generate_faq_answer
from app.retrieval.text_index import TextIndex


def faq_node(*, chroma_path: str | None = None):
    def node(state: dict) -> dict:
        index = TextIndex(chroma_path=chroma_path)
        index.index_faqs()
        hits = index.search_faq(state["query"], limit=2)
        fallback_answer = hits[0]["text"] if hits else "这个售后问题我还没有检索到准确答案。"
        answer = generate_faq_answer(
            query=state["query"],
            hits=hits,
            fallback=fallback_answer,
        )
        return {
            **state,
            "retrieved_items": hits,
            "answer": answer,
            "trace": state.get("trace", []) + [
                {"node": "faq", "hits": [hit["id"] for hit in hits], "llm_enabled": answer != fallback_answer}
            ],
        }

    return node
