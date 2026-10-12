from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.infraestructura.db.sesion import crear_tablas
from app.presentacion.rest import r_auth, r_proy, r_cred, r_tareas, r_arch, r_modelos, r_vista
from app.presentacion.oauth_google import router as google_router
from app.presentacion.ws import router as ws_router

from app.presentacion.seguridad_http import CabecerasSeguridad, LimiteAuth

app = FastAPI(title="VOOsk", version="0.1.0")

# Sin cookies de sesión (usamos Bearer JWT): no se permiten credenciales CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CabecerasSeguridad)
app.add_middleware(LimiteAuth)

app.include_router(r_auth)
app.include_router(google_router)
app.include_router(r_proy)
app.include_router(r_cred)
app.include_router(r_tareas)
app.include_router(r_arch)
app.include_router(r_modelos)
app.include_router(r_vista)
app.include_router(ws_router)


@app.on_event("startup")
def _startup():
    crear_tablas()
    # Recuperar tareas que quedaron colgadas en 'en_curso'
    # (ej: el servidor se reinició a mitad de una ejecución).
    try:
        from app.infraestructura.db.sesion import SessionLocal
        from app.infraestructura.db import modelos as M
        db = SessionLocal()
        try:
            colgadas = db.query(M.TaskSession).filter_by(estado="en_curso").all()
            for t in colgadas:
                t.estado = "fallida"
                t.resumen = ("Sesión interrumpida (el servidor se reinició a mitad "
                             "de la ejecución). Crea una tarea nueva.")
                db.add(M.TaskEvent(session_id=t.id, tipo="tarea_finalizada",
                                   datos={"resumen": t.resumen, "interrumpida": True}))
            if colgadas:
                db.commit()
                print(f"Recuperadas {len(colgadas)} tarea(s) interrumpida(s).")
        finally:
            db.close()
    except Exception as exc:
        print(f"Aviso: no se pudieron recuperar tareas colgadas: {exc}")
    if not settings.FERNET_KEY:
        print("AVISO SEGURIDAD: FERNET_KEY vacía — las BYOK se cifran con clave "
              "efímera y se pierden al reiniciar. Genera una con: "
              "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    if settings.JWT_SECRET == "cambia-este-secreto-en-produccion":
        print("AVISO SEGURIDAD: JWT_SECRET por defecto — cámbialo en producción.")


@app.get("/salud")
def salud():
    return {"ok": True, "servicio": "voosk"}
