from uuid import uuid4
from pathlib import Path

from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import REPORT_DIR, OLLAMA_MODELS
from app.database import get_db, SessionLocal
from app.auth.dependencies import get_current_user, require_login, require_admin
from app.models.user import User
from app.models.post import Post
from app.models.analysis import AnalysisFinding

from app.services.file_service import save_upload_file, prepare_analysis_target, count_python_files, count_java_files, count_c_cpp_files, count_source_files, read_source_code
from app.services.bandit_service import run_bandit, summarize_results
from app.services.ai_service import explain_issue
from app.services.mapping_service import map_vulnerability
from app.services.semgrep_service import run_semgrep, normalize_semgrep_results
from app.services.llm_service import analyze_with_llm
from app.services.scoring_service import calculate_security_score
from app.services.report_service import generate_report
from app.services.progress_service import TASKS, create_task, update_task, finish_task, fail_task

router = APIRouter()

def render(request: Request, template_name: str, context: dict | None = None):
    from app.main import templates
    data = {"request": request}
    if context:
        data.update(context)
    return templates.TemplateResponse(request, template_name, data)

@router.get("/")
def index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    recent_posts = {}
    for board_type in ["notice", "free", "resources", "qna"]:
        recent_posts[board_type] = (
            db.query(Post)
            .filter(Post.board_type == board_type)
            .order_by(Post.id.desc())
            .limit(5)
            .all()
        )

    total_findings = db.query(AnalysisFinding).count()

    top_weakness_rows = (
        db.query(
            AnalysisFinding.test_name,
            AnalysisFinding.issue_severity,
            func.count(AnalysisFinding.id).label("count"),
        )
        .group_by(AnalysisFinding.test_name, AnalysisFinding.issue_severity)
        .order_by(func.count(AnalysisFinding.id).desc())
        .limit(4)
        .all()
    )

    top_weaknesses = []
    for row in top_weakness_rows:
        count = int(row.count)
        ratio = int((count / total_findings) * 100) if total_findings else 0
        top_weaknesses.append(
            {"name": row.test_name, "severity": row.issue_severity, "count": count, "ratio": ratio}
        )

    return render(
        request,
        "index.html",
        {
            "current_user": current_user,
            "recent_posts": recent_posts,
            "top_weaknesses": top_weaknesses,
            "total_findings": total_findings,
        },
    )

@router.get("/upload")
def upload_page(request: Request, current_user: User = Depends(require_login)):
    return render(
        request,
        "upload.html",
        {
            "current_user": current_user,
            "models": OLLAMA_MODELS,
        },
    )

@router.post("/analyze/start")
async def analyze_start(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_name: str = Form(...),
    current_user: User = Depends(require_login),
):
    if model_name not in OLLAMA_MODELS:
        return JSONResponse({"error": "허용되지 않은 LLM 모델입니다."}, status_code=400)

    try:
        # UploadFile은 요청 종료 후 닫힐 수 있으므로 먼저 저장하고 경로만 백그라운드에 전달
        saved_path = save_upload_file(file)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    task_id = uuid4().hex
    create_task(task_id)

    background_tasks.add_task(
        run_analysis_task,
        task_id,
        str(saved_path),
        file.filename,
        model_name,
        current_user.username,
    )

    return {"task_id": task_id}

@router.get("/analyze/progress/{task_id}")
def analyze_progress(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        return {
            "status": "error",
            "progress": 0,
            "message": "작업을 찾을 수 없습니다.",
            "eta": "-",
            "result_url": None,
        }
    return {
        "status": task.get("status"),
        "progress": task.get("progress", 0),
        "message": task.get("message", ""),
        "eta": task.get("eta", "-"),
        "result_url": task.get("result_url"),
    }

@router.get("/analyze/result/{task_id}")
def analyze_result(
    task_id: str,
    request: Request,
    current_user: User = Depends(require_login),
):
    task = TASKS.get(task_id)
    if not task or not task.get("result"):
        return render(
            request,
            "upload.html",
            {
                "current_user": current_user,
                "models": OLLAMA_MODELS,
                "error": "분석 결과를 찾을 수 없습니다.",
            },
        )

    return render(
        request,
        "result.html",
        {
            "current_user": current_user,
            "result": task["result"],
        },
    )

# 기존 동기식 /analyze 호출이 남아 있어도 새 진행률 방식으로 안내
@router.post("/analyze")
async def analyze_redirect_notice(
    request: Request,
    current_user: User = Depends(require_login),
):
    return render(
        request,
        "upload.html",
        {
            "current_user": current_user,
            "models": OLLAMA_MODELS,
            "error": "분석은 화면의 진행률 방식으로 실행됩니다. 파일과 LLM 모델을 선택 후 다시 실행하세요.",
        },
    )


def run_analysis_task(task_id: str, saved_path_str: str, original_filename: str, model_name: str, username: str):
    db = SessionLocal()

    try:
        saved_path = Path(saved_path_str)

        update_task(task_id, 10, "분석 대상 준비 중")
        target_dir = prepare_analysis_target(saved_path)

        update_task(task_id, 18, "소스코드 파일 확인 중")
        python_file_count = count_python_files(target_dir)
        java_file_count = count_java_files(target_dir)
        c_cpp_file_count = count_c_cpp_files(target_dir)
        total_source_count = count_source_files(target_dir)

        if total_source_count == 0:
            fail_task(task_id, "분석 대상 소스코드 파일이 없습니다. 지원 확장자: .py, .java, .c, .cpp, .h, .hpp")
            return

        enriched_issues = []
        raw_errors = []

        if python_file_count > 0:
            update_task(task_id, 32, "Python Bandit 정적분석 실행 중")
            raw_bandit = run_bandit(target_dir)
            for issue in raw_bandit.get("results", []):
                enriched = dict(issue)
                enriched["tool"] = "Bandit"
                enriched["ai"] = explain_issue(issue)
                mapping = map_vulnerability(issue)
                enriched["cwe"] = mapping["cwe"]
                enriched["mois"] = mapping["mois"]
                enriched_issues.append(enriched)
            if raw_bandit.get("error"):
                raw_errors.append(raw_bandit.get("error"))

        if java_file_count > 0 or c_cpp_file_count > 0:
            update_task(task_id, 48, "Java/C/C++ Semgrep 정적분석 실행 중")
            raw_semgrep = run_semgrep(target_dir)
            for issue in normalize_semgrep_results(raw_semgrep):
                issue["ai"] = {
                    "cause": issue.get("issue_text", "Semgrep 탐지 결과"),
                    "impact": "해당 취약 패턴은 입력값 변조, 정보노출, 명령 실행 또는 메모리 손상으로 이어질 수 있습니다.",
                    "recommendation": "안전한 API 사용, 입력값 검증, 경계값 검사, 보안 코딩 기준 적용이 필요합니다.",
                }
                enriched_issues.append(issue)
            if raw_semgrep.get("error"):
                raw_errors.append(raw_semgrep.get("error"))

        update_task(task_id, 65, f"{model_name} LLM 보조 분석 중")
        code_text = read_source_code(target_dir, limit=6000)
        llm_result = analyze_with_llm(code_text, model_name)

        update_task(task_id, 78, "보안 점수 및 등급 산출 중")
        security = calculate_security_score(enriched_issues, llm_result)

        result = {
            "filename": original_filename,
            "python_file_count": python_file_count,
            "java_file_count": java_file_count,
            "c_cpp_file_count": c_cpp_file_count,
            "source_file_count": total_source_count,
            "total": len(enriched_issues),
            "summary": summarize_results(enriched_issues),
            "issues": enriched_issues,
            "error": " / ".join(raw_errors) if raw_errors else None,
            "llm_result": llm_result,
            "llm_model": model_name,
            "security": security,
            "report_file": None,
        }

        update_task(task_id, 88, "PDF 보고서 생성 중")
        report_name = f"security_report_{uuid4().hex}.pdf"
        report_path = REPORT_DIR / report_name
        generate_report(original_filename, result, str(report_path))
        result["report_file"] = report_name

        update_task(task_id, 95, "분석 결과 DB 저장 중")
        for issue in enriched_issues:
            finding = AnalysisFinding(
                username=username,
                filename=original_filename,
                test_id=issue.get("test_id"),
                test_name=issue.get("test_name", "Unknown Weakness"),
                issue_severity=issue.get("issue_severity", "LOW"),
                issue_confidence=issue.get("issue_confidence"),
                cwe=issue.get("cwe"),
                mois=issue.get("mois"),
                file_path=issue.get("filename"),
                line_number=issue.get("line_number"),
                score=security["score"],
                grade=security["grade"],
                report_path=report_name,
            )
            db.add(finding)

        db.commit()
        TASKS[task_id]["result"] = result
        finish_task(task_id, f"/analyze/result/{task_id}")

    except Exception as exc:
        fail_task(task_id, str(exc))

    finally:
        db.close()

@router.get("/reports/{report_name}")
def download_report(report_name: str, current_user: User = Depends(require_login)):
    path = REPORT_DIR / report_name
    if not path.exists():
        return {"error": "보고서를 찾을 수 없습니다."}
    return FileResponse(path=str(path), filename=report_name, media_type="application/pdf")

@router.get("/history")
def analysis_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    query = db.query(AnalysisFinding)
    if current_user.role != "admin":
        query = query.filter(AnalysisFinding.username == current_user.username)
    items = query.order_by(AnalysisFinding.id.desc()).limit(200).all()
    return render(request, "history.html", {"current_user": current_user, "items": items})

@router.get("/admin/users")
def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return render(request, "admin_users.html", {"current_user": current_user, "users": users})

@router.get("/admin/dashboard")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    total = db.query(AnalysisFinding).count()
    high = db.query(AnalysisFinding).filter(AnalysisFinding.issue_severity == "HIGH").count()
    medium = db.query(AnalysisFinding).filter(AnalysisFinding.issue_severity == "MEDIUM").count()
    low = db.query(AnalysisFinding).filter(AnalysisFinding.issue_severity == "LOW").count()

    top_mois = (
        db.query(AnalysisFinding.mois, func.count(AnalysisFinding.id).label("count"))
        .group_by(AnalysisFinding.mois)
        .order_by(func.count(AnalysisFinding.id).desc())
        .limit(10)
        .all()
    )

    return render(
        request,
        "admin_dashboard.html",
        {
            "current_user": current_user,
            "total": total,
            "high": high,
            "medium": medium,
            "low": low,
            "top_mois": top_mois,
        },
    )
