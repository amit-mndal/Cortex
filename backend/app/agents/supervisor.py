"""
Top-level multi-agent orchestration.

A Supervisor node reads the question and decides which specialist should
handle it, then that specialist's own subgraph/logic runs. This is the
LangGraph "supervisor" pattern - one router, several specialized workers.

    question
       |
       v
   [supervisor: classify]
       |
   +---+----+--------+
   |        |        |
  rag      web      data
   |        |        |
   +---+----+--------+
       |
    [answer]
"""
from typing import TypedDict, Literal
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.core.progress import publish_progress
from app.agents.rag_agent import run_rag_agent
from app.agents.web_agent import run_web_agent
from app.agents.data_agent import run_data_agent

from app.retrieval.vector_store import has_documents

llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0)

Route = Literal["rag", "web", "data", "chat"]


class SupervisorState(TypedDict):
    question: str
    route: Route
    answer: str
    sources: list[dict]
    retries: int
    job_id: str
    contexts: list[str]


CLASSIFY_PROMPT = """Classify the user's question into exactly one category. Reply with only the category word.

{doc_context}

Categories:
- rag: question that should be answered from uploaded documents. If documents have been uploaded, STRONGLY PREFER this category unless the question is clearly about live/current events or is a general greeting.
- web: question needing current/live internet information, only relevant if documents don't cover it
- data: question about analyzing/calculating from an uploaded spreadsheet/CSV
- chat: greetings or general conversation with no lookup needed

Question: {question}
Category:"""


def classify_node(state: SupervisorState) -> SupervisorState:
    publish_progress(state["job_id"], "classify", "Deciding which agent should handle this")
    doc_context = (
        "The user HAS uploaded documents that may be relevant."
        if has_documents() else
        "The user has NOT uploaded any documents."
    )
    result = llm.invoke(
        CLASSIFY_PROMPT.format(question=state["question"], doc_context=doc_context)
    ).content.strip().lower()
    route: Route = result if result in ("rag", "web", "data", "chat") else "rag"
    publish_progress(state["job_id"], "route", f"Routed to: {route} agent")
    return {**state, "route": route}


def rag_node(state: SupervisorState) -> SupervisorState:
    result = run_rag_agent(state["question"], job_id=state["job_id"])

    if not result["found"]:
        publish_progress(state["job_id"], "fallback_web", "Not in your documents — checking the web instead")
        web_result = run_web_agent(state["question"], job_id=state["job_id"])
        return {
            **state,
            "answer": web_result["answer"],
            "sources": web_result["sources"],
            "retries": result["retries"],
            "contexts": result["contexts"],
            "route": "web",
        }

    return {
        **state,
        "answer": result["answer"],
        "sources": result["sources"],
        "retries": result["retries"],
        "contexts": result["contexts"],
    }


def web_node(state: SupervisorState) -> SupervisorState:
    result = run_web_agent(state["question"], job_id=state["job_id"])
    return {**state, "answer": result["answer"], "sources": result["sources"], "retries": 0}


def data_node(state: SupervisorState) -> SupervisorState:
    result = run_data_agent(state["question"], job_id=state["job_id"])
    return {**state, "answer": result["answer"], "sources": result["sources"], "retries": 0}


def chat_node(state: SupervisorState) -> SupervisorState:
    publish_progress(state["job_id"], "generate", "Responding")
    answer = llm.invoke(state["question"]).content
    return {**state, "answer": answer, "sources": [], "retries": 0}


def route_selector(state: SupervisorState) -> str:
    return state["route"]


def build_supervisor_graph():
    graph = StateGraph(SupervisorState)
    graph.add_node("classify", classify_node)
    graph.add_node("rag", rag_node)
    graph.add_node("web", web_node)
    graph.add_node("data", data_node)
    graph.add_node("chat", chat_node)

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify", route_selector, {"rag": "rag", "web": "web", "data": "data", "chat": "chat"}
    )
    graph.add_edge("rag", END)
    graph.add_edge("web", END)
    graph.add_edge("data", END)
    graph.add_edge("chat", END)

    return graph.compile()


supervisor_app = build_supervisor_graph()


def run_supervisor(question: str, job_id: str = "") -> dict:
    result = supervisor_app.invoke({
        "question": question, "route": "rag", "answer": "", "sources": [], "retries": 0,
        "job_id": job_id, "contexts": [],
    })
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "retries": result["retries"],
        "route": result["route"],
        "contexts": result["contexts"],
    }
