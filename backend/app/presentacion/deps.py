from fastapi import Depends, HTTPException, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.infraestructura.db.sesion import get_db
from app.infraestructura.db.modelos import User
from app.infraestructura.seguridad.jwt import leer_token

_bearer = HTTPBearer(auto_error=False)

def usuario_actual(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                   db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(401, "Falta token Bearer")
    uid = leer_token(creds.credentials)
    if not uid:
        raise HTTPException(401, "Token inválido o expirado")
    u = db.get(User, uid)
    if not u:
        raise HTTPException(401, "Usuario no existe")
    return u

def usuario_ws(websocket: WebSocket, db: Session) -> User | None:
    token = websocket.query_params.get("token", "")
    uid = leer_token(token)
    return db.get(User, uid) if uid else None
