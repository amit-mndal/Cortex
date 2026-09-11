import subprocess
import sys
import tempfile
import os

TIMEOUT_SECONDS = 15

_RUNNER_TEMPLATE = """
import pandas as pd

df = pd.read_csv(r"{csv_path}")

try:
{indented_code}
    print("__RESULT_START__")
    print(result)
    print("__RESULT_END__")
except Exception as e:
    print("__ERROR__")
    print(str(e))
"""


def _indent(code: str) -> str:
    return "\n".join("    " + line for line in code.strip().splitlines())


def run_pandas_code(csv_path: str, code: str) -> dict:
    """Executes LLM-generated pandas code against a CSV in an isolated
    subprocess. The code must assign its final answer to a variable
    called `result`. Runs with a hard timeout so a bad/hanging script
    can't block the server.
    """
    script = _RUNNER_TEMPLATE.format(csv_path=csv_path, indented_code=_indent(code))

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        output = proc.stdout

        if "__ERROR__" in output:
            error_msg = output.split("__ERROR__")[1].strip()
            return {"success": False, "output": error_msg}

        if "__RESULT_START__" in output:
            result_text = output.split("__RESULT_START__")[1].split("__RESULT_END__")[0].strip()
            return {"success": True, "output": result_text}

        return {"success": False, "output": proc.stderr or "No result produced."}

    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Code execution timed out."}
    finally:
        os.unlink(script_path)
