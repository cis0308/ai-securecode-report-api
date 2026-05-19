from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.auth_service import create_user, authenticate_user
from app.auth.jwt_handler import create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter()

def render(request: Request, template_name: str, context: dict | None = None):
    from app.main import templates
    data = {"request": request}
    if context:
        data.update(context)
    return templates.TemplateResponse(request, template_name, data)

@router.get("/login")
def login_page(request: Request, current_user=Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    return render(request, "login.html", {"current_user": current_user})

@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username.strip(), password)
    if not user:
        return render(request, "login.html", {"error": "아이디 또는 비밀번호가 올바르지 않습니다.", "current_user": None})

    token = create_access_token({"sub": user.username, "role": user.role})
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 2,
    )
    return response

@router.get("/signup")
def signup_page(request: Request, current_user=Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    return render(request, "signup.html", {"current_user": current_user})

@router.post("/signup")
def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    username = username.strip()

    if len(username) < 3:
        return render(request, "signup.html", {"error": "아이디는 3자 이상 입력하세요.", "current_user": None})
    if len(password) < 6:
        return render(request, "signup.html", {"error": "비밀번호는 6자 이상 입력하세요.", "current_user": None})
    if password != password_confirm:
        return render(request, "signup.html", {"error": "비밀번호 확인이 일치하지 않습니다.", "current_user": None})

    try:
        create_user(db, username, password, "user")
    except ValueError as exc:
        return render(request, "signup.html", {"error": str(exc), "current_user": None})

    return RedirectResponse(url="/login?signup=success", status_code=302)

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response
