def calculate_security_score(issues: list[dict], llm_text: str = "") -> dict:
    score = 100

    for issue in issues:
        severity = issue.get("issue_severity", "LOW")
        if severity == "HIGH":
            score -= 10
        elif severity == "MEDIUM":
            score -= 5
        else:
            score -= 2

    if llm_text and "HIGH" in llm_text.upper():
        score -= 5

    score = max(score, 0)

    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    else:
        grade = "D"

    return {"score": score, "grade": grade}
