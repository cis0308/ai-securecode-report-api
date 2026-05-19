from sqlalchemy.orm import Session
from app.models.user import User
from app.auth.password import hash_password, verify_password

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, password: str, role: str = "user"):
    role = role if role in {"admin", "user"} else "user"

    existing = get_user_by_username(db, username)
    if existing:
        raise ValueError("이미 사용 중인 아이디입니다.")

    user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def create_default_admin(db: Session):
    admin = get_user_by_username(db, "admin")
    if admin:
        return admin
    return create_user(db, "admin", "admin1234", "admin")
