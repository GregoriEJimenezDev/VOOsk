"""Login con Google (OAuth2 Authorization Code).

Configuración (backend/.env):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
  GOOGLE_REDIRECT=http://localhost:8000/auth/google/callback (registrado en Google Cloud),
  FRONTEND_URL=http://localhost:5174

Flujo: frontend → GET /auth/google/url → redirige a Google →
Google → GET /auth/google/callback?code=… → crea/recupera usuario →
redirige al frontend /auth/callback?token=JWT.
"""
from __future__ import annotations
import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.infraestructura.db import modelos as M
from app.infraestructura.db.sesion import get_db
from app.infraestructura.seguridad.jwt import crear_token
from app.infraestructura.seguridad.passwords import hash_password

router = APIRouter(prefix="/auth/google", tags=["auth"])


def _configurado() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


@router.get("/url")
def google_url():
    if not _configurado():
        raise HTTPException(501, "Google OAuth no configurado en el servidor (ver README)")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {"url": url}


@router.get("/callback")
async def google_callback(code: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"{settings.FRONTEND_URL}/login?error=google")
    if not code or not _configurado():
        raise HTTPException(400, "Callback de Google inválido")
    async with httpx.AsyncClient(timeout=20) as c:
        tok = await c.post("https://oauth2.googleapis.com/token", data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT,
        })
        if tok.status_code != 200:
            raise HTTPException(400, "Google no validó el código")
        access = tok.json()["access_token"]
        ui = await c.get("https://openidconnect.googleapis.com/v1/userinfo",
                         headers={"Authorization": f"Bearer {access}"})
        if ui.status_code != 200:
            raise HTTPException(400, "No se pudo leer el perfil de Google")
        email = ui.json().get("email", "").lower().strip()
    if not email:
        raise HTTPException(400, "Google no devolvió email")

    db: Session = next(get_db())
    try:
        user = db.query(M.User).filter_by(email=email).first()
        if not user:
            user = M.User(email=email, password_hash=hash_password(secrets.token_urlsafe(32)))
            db.add(user)
            db.commit()
            db.refresh(user)
        token = crear_token(user.id)
    finally:
        db.close()
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?token={token}")
