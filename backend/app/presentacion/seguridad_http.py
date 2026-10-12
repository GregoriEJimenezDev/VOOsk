"""Cabeceras de seguridad + límite de intentos en /auth (anti fuerza bruta)."""
from __future__ import annotations
import time
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class CabecerasSeguridad(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return resp


class LimiteAuth(BaseHTTPMiddleware):
    """Máximo 30 POST a /auth/* por IP y minuto (memoria local, sin Redis)."""

    def __init__(self, app, max_req: int = 30, ventana: int = 60):
        super().__init__(app)
        self.max_req = max_req
        self.ventana = ventana
        self.hits: dict[str, list[float]] = {}

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/auth/") and request.method == "POST":
            ip = request.client.host if request.client else "?"
            ahora = time.time()
            q = [t for t in self.hits.get(ip, []) if ahora - t < self.ventana]
            if len(q) >= self.max_req:
                return JSONResponse({"detail": "Demasiados intentos, espera un minuto"}, 429)
            q.append(ahora)
            self.hits[ip] = q
        return await call_next(request)
