import os
import pandas as pd
from langchain_groq import ChatGroq
from app.core.config import settings
from app.core.progress import publish_progress
from app.tools.code_sandbox import run_pandas_code

llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0)
CSV_DIR = "./data/csvs"


def _latest_csv() -> str | None:
    if not os.path.isdir(CSV_DIR):
        return None
    files = [f for f in os.listdir(CSV_DIR) if f.endswith(".csv")]
    if not files:
        return None
    files.sort(key=lambda f: os.path.getmtime(os.path.join(CSV_DIR, f)), reverse=True)
    return os.path.join(CSV_DIR, files[0])


def run_data_agent(question: str, job_id: str = "") -> dict:
    csv_path = _latest_csv()
    if not csv_path:
        return {
            "answer": "No CSV has been uploaded yet. Upload a .csv file to ask data questions.",
            "sources": [],
        }

    publish_progress(job_id, "analyze", "Inspecting the dataset schema")
    preview = pd.read_csv(csv_path, nrows=5)
    schema = f"Columns: {list(preview.columns)}\nSample rows:\n{preview.to_string(index=False)}"

    prompt = (
        f"You are given a pandas DataFrame called `df` with this schema:\n{schema}\n\n"
        f"Write Python/pandas code to answer: \"{question}\"\n"
        "Assign the final answer to a variable named `result`. "
        "Only output the code, no explanation, no markdown fences."
    )
    code = llm.invoke(prompt).content.strip().strip("```python").strip("```")

    publish_progress(job_id, "execute", "Running analysis code in sandbox")
    exec_result = run_pandas_code(csv_path, code)

    if not exec_result["success"]:
        return {
            "answer": f"The analysis code failed: {exec_result['output']}",
            "sources": [{"index": 1, "filename": os.path.basename(csv_path), "text": code[:200]}],
        }

    publish_progress(job_id, "generate", "Writing the answer")
    explain_prompt = (
        f"Question: {question}\nComputed result: {exec_result['output']}\n"
        "Write a one to two sentence natural-language answer using this result."
    )
    answer = llm.invoke(explain_prompt).content

    return {
        "answer": answer,
        "sources": [{"index": 1, "filename": os.path.basename(csv_path), "text": f"code: {code[:150]}"}],
    }
