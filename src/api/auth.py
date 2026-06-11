"""注册 / 登录 / 游客用户列表"""
import hashlib, uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User

router = APIRouter(tags=["auth"])

def _hash(password: str) -> str:
    salt = "lc_recycle_2026"
    return hashlib.sha256((password + salt).encode()).hexdigest()

@router.post("/auth/register")
def register(nickname: str, password: str, db: Session = Depends(get_db)):
    nickname = nickname.strip()
    if len(nickname) < 2 or len(nickname) > 20:
        raise HTTPException(status_code=400, detail="昵称需 2-20 个字符")
    if len(password) < 4 or len(password) > 32:
        raise HTTPException(status_code=400, detail="密码需 4-32 个字符")
    exists = db.query(User).filter(User.nickname == nickname, User.password_hash.isnot(None)).first()
    if exists:
        raise HTTPException(status_code=400, detail="该昵称已被注册")
    uid = str(uuid.uuid4())[:8]
    user = User(openid=f"reg_{uid}", nickname=nickname, role="student", password_hash=_hash(password))
    db.add(user); db.commit(); db.refresh(user)
    return {"ok": True, "user": _user_json(user), "msg": "注册成功！"}

@router.get("/auth/login")
def login(nickname: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.nickname == nickname, User.password_hash.isnot(None)).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或未注册")
    if user.password_hash != _hash(password):
        raise HTTPException(status_code=401, detail="密码错误")
    return {"ok": True, "user": _user_json(user)}

@router.get("/auth/guests")
def list_guests(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.password_hash.is_(None)).order_by(User.role == "admin", User.id).all()
    return {"guests": [_user_json(u) for u in users]}

def _user_json(u: User) -> dict:
    return {"id": u.id, "nickname": u.nickname, "role": u.role, "carbon_score": u.carbon_score, "registered": u.password_hash is not None}
