"""
Agentic RAG graph (Corrective RAG pattern).

Flow:
  retrieve -> grade -> (relevant? generate : rewrite -> retrieve)  [loops up to N times]

This is what makes the system "agentic" rather than plain RAG: the agent
inspects its own retrieval quality and decides whether to try again,
instead of blindly answering with whatever it found.
"""
from typing import TypedDict
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.core.progress import publish_progress
from app.retrieval.hybrid_search import hybrid_retrieve

llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0.2)


class AgentState(TypedDict):
    question: str
    search_query: str
    retries: int
    chunks: list[dict]
    is_relevant: bool
    answer: str
    sources: list[dict]
    job_id: str


def retrieve_node(state: AgentState) -> AgentState:
    publish_progress(state["job_id"], "retrieve", f"Searching documents for: {state['search_query']}")
    chunks = hybrid_retrieve(state["search_query"], top_k=settings.top_k)
    return {**state, "chunks": chunks}


def grade_node(state: AgentState) -> AgentState:
    publish_progress(state["job_id"], "grade", "Checking whether retrieved chunks are relevant")
    if not state["chunks"]:
        return {**state, "is_relevant": False}

    context = "\n\n".join(c["text"][:300] for c in state["chunks"])
    prompt = (
        f"Question: {state['question']}\n\n"
        f"Retrieved context:\n{context}\n\n"
        "Does this context contain enough information to actually answer the "
        "question? Reply with exactly one word: YES or NO."
    )
    verdict = llm.invoke(prompt).content.strip().upper()
    return {**state, "is_relevant": verdict.startswith("YES")}


def rewrite_node(state: AgentState) -> AgentState:
    publish_progress(state["job_id"], "rewrite", "Retrieval was weak — rewriting the search query")
    prompt = (
        f"Original question: {state['question']}\n"
        f"Previous search query: {state['search_query']}\n"
        "The previous search did not return useful results. Rewrite this as a "
        "better, more specific search query (just the query, nothing else)."
    )
    new_query = llm.invoke(prompt).content.strip()
    return {**state, "search_query": new_query, "retries": state["retries"] + 1}


def generate_node(state: AgentState) -> AgentState:
    publish_progress(state["job_id"], "generate", "Writing the answer")
    if not state["chunks"]:
        return {
            **state,
            "answer": "I couldn't find relevant information in the uploaded documents to answer this.",
            "sources": [],
        }

    context = "\n\n".join(f"[{i+1}] {c['text']}" for i, c in enumerate(state["chunks"]))
    prompt = (
        f"Answer the question using ONLY the context below. Cite sources using "
        f"[1], [2] etc. matching the numbered context. If the context is "
        f"insufficient, say so honestly.\n\n"
        f"Context:\n{context}\n\nQuestion: {state['question']}\n\nAnswer:"
    )
    answer = llm.invoke(prompt).content
    sources = [{"index": i + 1, "filename": c["metadata"]["filename"], "page": c["metadata"].get("page"),
            "text": c["text"][:200]} for i, c in enumerate(state["chunks"])]
    
    # sources = [{"index": i + 1, "filename": c["metadata"]["filename"], "text": c["text"][:200]}
    #            for i, c in enumerate(state["chunks"])]
    return {**state, "answer": answer, "sources": sources}


def route_after_grade(state: AgentState) -> str:
    if state["is_relevant"]:
        return "generate"
    if state["retries"] >= settings.max_retrieval_retries:
        return "generate"  # give up gracefully, generate() handles empty/weak context
    return "rewrite"


def build_rag_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("grade", grade_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges("grade", route_after_grade, {"generate": "generate", "rewrite": "rewrite"})
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("generate", END)

    return graph.compile()


rag_app = build_rag_graph()


def run_rag_agent(question: str, job_id: str = "") -> dict:
    result = rag_app.invoke({
        "question": question,
        "search_query": question,
        "retries": 0,
        "chunks": [],
        "is_relevant": False,
        "answer": "",
        "sources": [],
        "job_id": job_id,
    })
    contexts = [c["text"] for c in result["chunks"]]
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "retries": result["retries"],
        "contexts": contexts,
        "found": bool(result["chunks"]),
    }
