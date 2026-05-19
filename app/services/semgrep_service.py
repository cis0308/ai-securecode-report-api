import json
import subprocess
from pathlib import Path
from app.config import SEMGREP_RULE_FILE

SEVERITY_MAP = {"ERROR": "HIGH", "WARNING": "MEDIUM", "INFO": "LOW"}

def run_semgrep(target_dir: Path) -> dict:
    cmd = ["semgrep", "--config", str(SEMGREP_RULE_FILE), "--json", "--quiet", str(target_dir)]
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180
        )
        data = json.loads(completed.stdout.strip() or "{}")
        data["returncode"] = completed.returncode
        data["stderr"] = completed.stderr
        return data
    except FileNotFoundError:
        return {"results": [], "error": "Semgrep가 설치되어 있지 않습니다. pip install semgrep 후 다시 실행하세요."}
    except subprocess.TimeoutExpired:
        return {"results": [], "error": "Semgrep 분석 시간이 초과되었습니다."}
    except Exception as exc:
        return {"results": [], "error": f"Semgrep 분석 실패: {exc}"}

def normalize_semgrep_results(raw: dict) -> list[dict]:
    items = []
    for item in raw.get("results", []):
        extra = item.get("extra", {})
        metadata = extra.get("metadata", {})
        severity = SEVERITY_MAP.get(str(extra.get("severity", "INFO")).upper(), "LOW")
        items.append({
            "tool": "Semgrep",
            "test_id": item.get("check_id", "semgrep-rule"),
            "test_name": item.get("check_id", "Semgrep Rule"),
            "issue_severity": severity,
            "issue_confidence": "MEDIUM",
            "issue_text": extra.get("message", "Semgrep 탐지 결과"),
            "filename": item.get("path", ""),
            "line_number": item.get("start", {}).get("line", 0),
            "cwe": metadata.get("cwe", "미매핑"),
            "mois": metadata.get("mois", "기타 보안약점"),
        })
    return items
