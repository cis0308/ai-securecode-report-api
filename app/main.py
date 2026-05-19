from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.auth.auth_router import router as auth_router
from app.routers.web import router as web_router
from app.routers.board import router as board_router
from app.auth.auth_service import create_default_admin
import app.models

app = FastAPI(title="AI SecureCode Report v13")

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

Base.metadata.create_all(bind=engine)

def init_default_admin():
    db: Session = SessionLocal()
    try:
        create_default_admin(db)
    finally:
        db.close()

init_default_admin()

app.include_router(auth_router)
app.include_router(web_router)
app.include_router(board_router)
