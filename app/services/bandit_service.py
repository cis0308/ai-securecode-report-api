import json
import subprocess
import sys
from pathlib import Path

def run_bandit(target_dir: Path) -> dict:
    command = [sys.executable, "-m", "bandit", "-r", str(target_dir), "-f", "json"]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if not stdout:
        return {"metrics": {}, "results": [], "error": stderr or "Bandit 실행 결과가 없습니다."}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"metrics": {}, "results": [], "error": stdout[:1000]}

def summarize_results(results: list[dict]) -> dict:
    summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNDEFINED": 0}
    for item in results:
        severity = item.get("issue_severity", "UNDEFINED")
        summary[severity] = summary.get(severity, 0) + 1
    return summary
