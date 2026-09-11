from langchain_groq import ChatGroq
from app.core.config import settings
from app.core.progress import publish_progress
from app.tools.web_search_tool import web_search

llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0.2)


def run_web_agent(question: str, job_id: str = "") -> dict:
    publish_progress(job_id, "web_search", f"Searching the web for: {question}")
    results = web_search(question, max_results=5)

    if not results:
        return {"answer": "I couldn't find anything relevant on the web for this.", "sources": []}

    context = "\n\n".join(
        f"[{i+1}] {r['title']}\n{r['snippet']}" for i, r in enumerate(results)
    )
    publish_progress(job_id, "generate", "Synthesizing answer from search results")
    prompt = (
        f"Answer the question using the web search results below. Cite sources "
        f"using [1], [2] etc.\n\nResults:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    )
    answer = llm.invoke(prompt).content

    sources = [
        {"index": i + 1, "filename": r["url"], "text": r["snippet"][:200]}
        for i, r in enumerate(results)
    ]
    return {"answer": answer, "sources": sources}
