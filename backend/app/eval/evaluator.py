"""
Evaluation layer: scores every RAG answer on two axes, using an
LLM-as-judge pattern (the same core technique the RAGAS library uses):

- faithfulness: is the answer actually supported by the retrieved context,
  or did the model add unsupported claims (hallucinate)?
- relevance: does the answer actually address the question asked?

This is implemented directly (two focused judge prompts) rather than via
the `ragas` package, to keep the dependency footprint small and the scoring
logic fully transparent/debuggable. `ragas` (pip install ragas) is a
drop-in upgrade later: same inputs (question, answer, contexts), same
0-1 output scale - see README for the swap-in path.
"""
import re
from langchain_groq import ChatGroq
from app.core.config import settings

judge_llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0)


def _extract_score(text: str) -> float:
    match = re.search(r"(\d+(\.\d+)?)", text)
    if not match:
        return 0.5
    score = float(match.group(1))
    return max(0.0, min(1.0, score / 10 if score > 1 else score))


FAITHFULNESS_PROMPT = """You are a strict evaluator. Given a context and an answer,
score from 0 to 10 how well the answer is supported ONLY by the context
(not outside knowledge). 10 = every claim is directly backed by the context.
0 = the answer contains claims not found in the context at all.

Context:
{context}

Answer:
{answer}

Reply with only a number 0-10."""

RELEVANCE_PROMPT = """You are a strict evaluator. Score from 0 to 10 how directly
the answer addresses the question asked (ignore factual correctness, only
judge relevance/on-topic-ness).

Question: {question}
Answer: {answer}

Reply with only a number 0-10."""


def evaluate_answer(question: str, answer: str, contexts: list[str]) -> dict:
    context_text = "\n\n".join(contexts)[:3000] or "(no context retrieved)"

    faithfulness_raw = judge_llm.invoke(
        FAITHFULNESS_PROMPT.format(context=context_text, answer=answer)
    ).content
    relevance_raw = judge_llm.invoke(
        RELEVANCE_PROMPT.format(question=question, answer=answer)
    ).content

    return {
        "faithfulness_score": _extract_score(faithfulness_raw),
        "relevance_score": _extract_score(relevance_raw),
    }
