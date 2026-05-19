from app.database import SessionLocal
from app.models.user import User

db = SessionLocal()

try:
    username = input("관리자로 변경할 아이디 입력: ").strip()
    user = db.query(User).filter(User.username == username).first()

    if not user:
        print("사용자를 찾을 수 없습니다.")
    else:
        user.role = "admin"
        db.commit()
        print(f"{username} 사용자를 관리자로 변경했습니다.")
finally:
    db.close()
