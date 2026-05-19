from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

RULE_DIR = BASE_DIR / "app" / "rules"
RULE_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"
TEMP_DIR = BASE_DIR / "temp"

UPLOAD_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./securecode.db"
)

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "CHANGE-ME-IN-PRODUCTION"
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

ALLOWED_EXTENSIONS = {
    ".py",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".zip"
}

SOURCE_EXTENSIONS = {
    ".py",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
}
# =========================
# External LLM API
# =========================

EXTERNAL_LLM_API_URL = os.getenv(
    "EXTERNAL_LLM_API_URL",
    "https://openrouter.ai/api/v1/chat/completions"
)

EXTERNAL_LLM_API_KEY = os.getenv(
    "EXTERNAL_LLM_API_KEY",
    ""
)

EXTERNAL_LLM_MODEL = os.getenv(
    "EXTERNAL_LLM_MODEL",
    "openai/gpt-4o-mini"
)

# 사용자 선택 모델 목록
EXTERNAL_LLM_MODELS = [
    "openai/gpt-5.4-mini",
    "openai/gpt-4.1-mini",
    "anthropic/claude-sonnet-4.6",
    "google/gemini-2.5-pro",
    "meta-llama/llama-3.3-70b-instruct:free",
]

# 기존 코드 호환
OLLAMA_MODELS = EXTERNAL_LLM_MODELS

LLM_CODE_LIMIT = int(
    os.getenv("LLM_CODE_LIMIT", "6000")
)

SEMGREP_RULE_FILE = RULE_DIR / "semgrep_multilang.yml"
TASK_EXPIRE_MINUTES = 60
