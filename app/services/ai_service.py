def explain_issue(issue: dict) -> dict:
    test_name = issue.get("test_name", "보안약점")
    severity = issue.get("issue_severity", "LOW")
    text = issue.get("issue_text", "")

    return {
        "cause": f"{test_name} 항목과 관련된 코드 사용이 탐지되었습니다. {text}",
        "impact": "해당 코드가 외부 입력, 파일, 명령 실행, 인증 정보 처리와 결합될 경우 보안위험으로 확대될 수 있습니다.",
        "recommendation": "검증된 안전한 API 사용, 입력값 검증, 예외 처리, 최소 권한 원칙 적용 여부를 확인하세요.",
        "fix_example": "# 수정 예시는 실제 코드 문맥을 확인한 뒤 적용해야 합니다.",
        "report_text": f"{severity} 등급의 잠재 보안약점이 확인되었으며, 코드 검토 및 보완 조치가 필요합니다.",
    }
