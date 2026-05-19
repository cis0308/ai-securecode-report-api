from pathlib import Path
from uuid import uuid4
import shutil
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import require_login
from app.models.user import User
from app.models.post import Post
from app.config import UPLOAD_DIR

router = APIRouter(prefix="/boards", tags=["boards"])

BOARD_INFO = {
    "notice": {"name": "공지사항", "desc": "서비스 안내, 업데이트, 보안 공지사항을 확인합니다.", "admin_only_write": True},
    "free": {"name": "자유 게시판", "desc": "사용자 간 자유롭게 의견을 공유합니다.", "admin_only_write": False},
    "resources": {"name": "자료실", "desc": "보안점검, Python 개발, 분석자료를 공유합니다.", "admin_only_write": False},
    "qna": {"name": "Q&A 게시판", "desc": "서비스 이용, 분석 오류, 보안약점 관련 질문을 등록합니다.", "admin_only_write": False},
}

def render(request: Request, template_name: str, context: dict | None = None):
    from app.main import templates
    data = {"request": request}
    if context:
        data.update(context)
    return templates.TemplateResponse(request, template_name, data)

def get_board_or_404(board_type: str):
    board = BOARD_INFO.get(board_type)
    if not board:
        raise HTTPException(status_code=404, detail="존재하지 않는 게시판입니다.")
    return board

def ensure_write_permission(board_type: str, current_user: User):
    board = get_board_or_404(board_type)
    if board.get("admin_only_write") and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="공지사항은 관리자만 작성할 수 있습니다.")

def save_attachment(file: UploadFile | None):
    if not file or not file.filename:
        return None, None

    board_upload_dir = UPLOAD_DIR / "board_files"
    board_upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename).name
    saved_name = f"{uuid4().hex}_{safe_name}"
    saved_path = board_upload_dir / saved_name

    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return safe_name, str(saved_path)

@router.get("/{board_type}")
def list_posts(
    board_type: str,
    request: Request,
    keyword: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    board = get_board_or_404(board_type)
    query = db.query(Post).filter(Post.board_type == board_type)
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        query = query.filter((Post.title.like(like)) | (Post.content.like(like)))
    posts = query.order_by(Post.id.desc()).all()
    return render(request, "board_list.html", {"current_user": current_user, "board_type": board_type, "board": board, "posts": posts, "keyword": keyword})

@router.get("/{board_type}/write")
def write_page(board_type: str, request: Request, current_user: User = Depends(require_login)):
    board = get_board_or_404(board_type)
    ensure_write_permission(board_type, current_user)
    return render(request, "board_form.html", {"current_user": current_user, "board_type": board_type, "board": board})

@router.post("/{board_type}/write")
def create_post(
    board_type: str,
    title: str = Form(...),
    content: str = Form(...),
    attachment: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    get_board_or_404(board_type)
    ensure_write_permission(board_type, current_user)
    attachment_name, attachment_path = save_attachment(attachment)
    post = Post(board_type=board_type, title=title.strip(), content=content.strip(), author_id=current_user.id, attachment_name=attachment_name, attachment_path=attachment_path)
    db.add(post)
    db.commit()
    db.refresh(post)
    return RedirectResponse(url=f"/boards/{board_type}/{post.id}", status_code=302)

@router.get("/{board_type}/{post_id}")
def detail_post(
    board_type: str,
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    board = get_board_or_404(board_type)
    post = db.query(Post).filter(Post.id == post_id, Post.board_type == board_type).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    post.view_count = (post.view_count or 0) + 1
    db.commit()
    db.refresh(post)
    can_delete = current_user.role == "admin" or post.author_id == current_user.id
    return render(request, "board_detail.html", {"current_user": current_user, "board_type": board_type, "board": board, "post": post, "can_delete": can_delete})

@router.post("/{board_type}/{post_id}/delete")
def delete_post(
    board_type: str,
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    get_board_or_404(board_type)
    post = db.query(Post).filter(Post.id == post_id, Post.board_type == board_type).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if current_user.role != "admin" and post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")
    db.delete(post)
    db.commit()
    return RedirectResponse(url=f"/boards/{board_type}", status_code=302)

@router.get("/{board_type}/{post_id}/download")
def download_attachment(
    board_type: str,
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    get_board_or_404(board_type)
    post = db.query(Post).filter(Post.id == post_id, Post.board_type == board_type).first()
    if not post or not post.attachment_path:
        raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다.")
    return FileResponse(path=post.attachment_path, filename=post.attachment_name, media_type="application/octet-stream")
