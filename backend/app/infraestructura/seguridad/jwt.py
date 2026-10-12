from datetime import datetime, timedelta, timezone
from jose import jwt
from app.config import settings

def crear_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_MINUTOS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def leer_token(token: str) -> int | None:
    try:
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return int(data["sub"])
    except Exception:
        return None
