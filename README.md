# AI SecureCode Report v23 Internal Multi-language Edition

내장형 LLM(Ollama) 분석 버전입니다.

## 변경사항
- Python: Bandit 분석 유지
- Java: Semgrep 분석 추가
- C/C++: Semgrep 분석 추가
- 지원 확장자: .py, .java, .c, .cpp, .h, .hpp, .zip
- 외부 API 호출 버전은 사용하지 않음
- Semgrep 로컬 룰셋 포함: app/rules/semgrep_multilang.yml

## 설치
```bash
pip install -r requirements.txt
```

## Semgrep 확인
```bash
semgrep --version
```

## 실행
```bash
python run.py
```
