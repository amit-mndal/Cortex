from fastapi import APIRouter
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import EvalScore

router = APIRouter()


@router.get("/evals")
def list_evals(limit: int = 20):
    session = get_session()
    try:
        rows = session.execute(
            select(EvalScore).order_by(EvalScore.created_at.desc()).limit(limit)
        ).scalars().all()
        return [
            {
                "job_id": r.job_id,
                "question": r.question,
                "faithfulness_score": r.faithfulness_score,
                "relevance_score": r.relevance_score,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        session.close()


@router.get("/evals/summary")
def evals_summary():
    session = get_session()
    try:
        rows = session.execute(select(EvalScore)).scalars().all()
        if not rows:
            return {"count": 0, "avg_faithfulness": None, "avg_relevance": None}
        avg_f = sum(r.faithfulness_score for r in rows) / len(rows)
        avg_r = sum(r.relevance_score for r in rows) / len(rows)
        return {"count": len(rows), "avg_faithfulness": round(avg_f, 2), "avg_relevance": round(avg_r, 2)}
    finally:
        session.close()


from app.cache.semantic_cache import clear_cache as _clear_cache

@router.post("/cache/clear")
def clear_cache_endpoint():
    _clear_cache()
    return {"status": "cache cleared"}