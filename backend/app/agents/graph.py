from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.chitchat import chitchat_node
from app.agents.compare import compare_node
from app.agents.decision_guide import decision_guide_node
from app.agents.faq import faq_node
from app.agents.intent_router import classify_intent
from app.agents.order import order_node
from app.agents.product_knowledge import product_knowledge_node
from app.agents.purchase import purchase_help_node
from app.agents.shopping_guide import shopping_guide_node
from app.agents.state import AgentState
from app.agents.supervisor import build_supervisor_trace


MORE_OPTIONS_FOLLOWUP_WORDS = [
    "还有",
    "其他",
    "别的",
    "换一批",
    "再推荐",
    "再找",
    "有没有",
]

COMPARE_FOLLOWUP_WORDS = [
    "区别",
    "差别",
    "对比",
    "比较",
    "哪个好",
    "哪款好",
    "哪个更",
    "怎么选",
]


def router_node(state: AgentState) -> AgentState:
    result = classify_intent(state["query"])
    intent = result.intent
    memory = state.get("memory", {})
    query = state["query"].lower()
    if intent == "clarification" and _contains_any(query, MORE_OPTIONS_FOLLOWUP_WORDS):
        intent = "shopping_guide"
    elif intent == "clarification" and memory.get("category"):
        intent = "shopping_guide"
    elif intent == "clarification" and len(memory.get("last_product_ids", [])) >= 2 and _contains_any(query, COMPARE_FOLLOWUP_WORDS):
        intent = "compare"
    supervisor_trace = build_supervisor_trace(
        query=state["query"],
        intent=intent,
        memory=memory,
        has_image=bool(state.get("image_path")),
    )
    return {
        **state,
        "intent": intent,
        "constraints": result.constraints.model_dump(),
        "trace": state.get("trace", []) + [
            supervisor_trace,
            {"node": "intent_router", "intent": intent, "confidence": result.confidence}
        ],
    }


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "decision_guide":
        return "decision_guide"
    if intent == "shopping_guide":
        return "shopping_guide"
    if intent == "product_knowledge":
        return "product_knowledge"
    if intent == "compare":
        return "compare"
    if intent == "order_query":
        return "order"
    if intent == "purchase_help":
        return "purchase_help"
    if intent == "faq":
        return "faq"
    if intent == "clarification":
        return "clarification"
    return "chitchat"


def clarification_node(state: AgentState) -> AgentState:
    return {
        **state,
        "answer": "我需要再确认一下：你想要推荐商品、对比商品、查询订单，还是了解某个商品参数？",
        "product_cards": [],
        "retrieved_items": [],
        "trace": state.get("trace", []) + [{"node": "clarification"}],
    }


def create_agent_graph(db: Session, *, chroma_path: str | None = None):
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", router_node)
    graph.add_node("decision_guide", decision_guide_node(db))
    graph.add_node("shopping_guide", shopping_guide_node(db))
    graph.add_node("product_knowledge", product_knowledge_node(db, chroma_path=chroma_path))
    graph.add_node("compare", compare_node(db))
    graph.add_node("order", order_node(db))
    graph.add_node("purchase_help", purchase_help_node(db))
    graph.add_node("faq", faq_node(chroma_path=chroma_path))
    graph.add_node("clarification", clarification_node)
    graph.add_node("chitchat", chitchat_node)
    graph.set_entry_point("intent_router")
    graph.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "decision_guide": "decision_guide",
            "shopping_guide": "shopping_guide",
            "product_knowledge": "product_knowledge",
            "compare": "compare",
            "order": "order",
            "purchase_help": "purchase_help",
            "faq": "faq",
            "clarification": "clarification",
            "chitchat": "chitchat",
        },
    )
    graph.add_edge("decision_guide", END)
    graph.add_edge("shopping_guide", END)
    graph.add_edge("product_knowledge", END)
    graph.add_edge("compare", END)
    graph.add_edge("order", END)
    graph.add_edge("purchase_help", END)
    graph.add_edge("faq", END)
    graph.add_edge("clarification", END)
    graph.add_edge("chitchat", END)
    return graph.compile()


def run_agent(
    db: Session,
    query: str,
    *,
    memory: dict | None = None,
    chroma_path: str | None = None,
) -> AgentState:
    app = create_agent_graph(db, chroma_path=chroma_path)
    return app.invoke(
        {
            "query": query,
            "messages": [{"role": "user", "content": query}],
            "memory": memory or {},
            "trace": [],
        }
    )


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
