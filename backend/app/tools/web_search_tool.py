# from duckduckgo_search import DDGS
from ddgs import DDGS


# def web_search(query: str, max_results: int = 5) -> list[dict]:
#     """Free web search, no API key needed. Used when the RAG documents
#     don't have the answer and the agent needs live internet info."""
#     with DDGS() as ddgs:
#         results = list(ddgs.text(query, max_results=max_results))
#     return [
#         {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
#         for r in results
#     ]

def web_search(query: str, max_results: int = 5) -> list[dict]:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, backend="html"))
    except Exception as e:
        print(f"[web_search_tool] search failed: {e}")
        return []

    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in results
    ]