import requests

from app.config import (
    EXTERNAL_LLM_API_URL,
    EXTERNAL_LLM_API_KEY,
    LLM_CODE_LIMIT,
)

def analyze_with_llm(code: str, model_name: str):

    if not code.strip():
        return "LLM 분석 대상 코드가 없습니다."

    if not EXTERNAL_LLM_API_KEY:
        return (
            "외부 LLM API Key가 설정되지 않았습니다. "
            "EXTERNAL_LLM_API_KEY 환경변수를 설정하세요."
        )

    system_prompt = """
너는 소프트웨어 보안약점 분석 전문가다.

Python, Java, C/C++ 코드를 분석하여:
- 보안약점
- CWE
- 공격 가능성
- 위험도
- 개선방안
- 수정 권고사항
을 설명한다.
"""

    user_prompt = f"""
다음 코드를 보안 관점에서 분석하라.

코드:
{code[:LLM_CODE_LIMIT]}

출력 형식:
1. 주요 보안약점
2. 위험도
3. 관련 CWE
4. 공격 가능성
5. 개선방안
6. 수정 예시
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {EXTERNAL_LLM_API_KEY}",

        # OpenRouter 권장 헤더
        "HTTP-Referer": "http://localhost",
        "X-Title": "AI SecureCode Report"
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(
            EXTERNAL_LLM_API_URL,
            headers=headers,
            json=payload,
            timeout=180
        )

        if response.status_code == 200:

            data = response.json()

            choices = data.get("choices", [])

            if not choices:
                return "LLM 응답이 비어 있습니다."

            return choices[0]["message"]["content"]

        return (
            f"LLM 분석 실패: "
            f"HTTP {response.status_code} - "
            f"{response.text[:1000]}"
        )

    except Exception as exc:
        return f"외부 LLM API 호출 실패: {exc}"