import json
from app.workers.celery_app import celery_app
from app.agents.supervisor import run_supervisor
from app.core.progress import get_redis, publish_progress, end_job
from app.cache.semantic_cache import check_cache, store_cache
from app.eval.evaluator import evaluate_answer
from app.db.session import get_session, init_db
from app.db.models import EvalScore

init_db()


@celery_app.task(name="run_agent_job")
def run_agent_job(job_id: str, question: str) -> None:
    """Runs in a separate Celery worker process, not the FastAPI request
    thread - so a slow multi-step agent run never blocks the API."""
    try:
        cached = check_cache(question)
        if cached is not None:
            publish_progress(job_id, "cache_hit", "Found a similar question answered recently - reusing it")
            result = {**cached, "from_cache": True}
            get_redis().set(f"job:{job_id}:result", json.dumps(result), ex=3600)
            return

        result = run_supervisor(question, job_id=job_id)
        result["from_cache"] = False
        get_redis().set(f"job:{job_id}:result", json.dumps(result), ex=3600)

        # Only RAG answers have retrieved context to judge faithfulness against.
        if result.get("route") == "rag":
            publish_progress(job_id, "evaluate", "Scoring answer quality (faithfulness & relevance)")
            contexts = result.get("contexts", [s["text"] for s in result.get("sources", [])])
            scores = evaluate_answer(question, result["answer"], contexts)

            session = get_session()
            try:
                session.add(EvalScore(
                    job_id=job_id,
                    question=question,
                    answer=result["answer"],
                    route=result["route"],
                    faithfulness_score=scores["faithfulness_score"],
                    relevance_score=scores["relevance_score"],
                    from_cache=False,
                ))
                session.commit()
            finally:
                session.close()

            result["eval"] = scores
            get_redis().set(f"job:{job_id}:result", json.dumps(result), ex=3600)

        store_cache(question, result)


    except Exception as e:
        import traceback
        traceback.print_exc()  # prints the FULL error + line number to this terminal
        get_redis().set(f"job:{job_id}:result", json.dumps({"error": str(e)}), ex=3600)
    # except Exception as e:
    #     get_redis().set(f"job:{job_id}:result", json.dumps({"error": str(e)}), ex=3600)
    finally:
        end_job(job_id)
