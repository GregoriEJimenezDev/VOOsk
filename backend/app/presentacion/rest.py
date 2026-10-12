"""Routers REST: auth, proyectos, credenciales, tareas/historial."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.infraestructura.db.sesion import get_db
from app.infraestructura.db import modelos as M
from app.infraestructura.seguridad.passwords import hash_password, verificar_password
from app.infraestructura.seguridad.jwt import crear_token, leer_token
from app.infraestructura.seguridad import crypto
from app.presentacion import schemas as S
from app.presentacion.deps import usuario_actual
from app.config import settings

r_auth = APIRouter(prefix="/auth", tags=["auth"])
r_proy = APIRouter(prefix="/proyectos", tags=["proyectos"])
r_cred = APIRouter(prefix="/credenciales", tags=["credenciales"])
r_tareas = APIRouter(prefix="/tareas", tags=["tareas"])
r_arch = APIRouter(prefix="/archivos", tags=["archivos"])
r_modelos = APIRouter(prefix="/modelos", tags=["modelos"])
r_vista = APIRouter(prefix="/vista", tags=["vista"])


@r_modelos.get("/estado")
def estado_modelos(db: Session = Depends(get_db), u=Depends(usuario_actual)):
    """Qué modelos reales están disponibles para este usuario (guía el modo demo)."""
    import httpx
    ollama_ok, ollama_modelos = False, []
    try:
        r = httpx.get(f"{settings.OLLAMA_URL.rstrip('/')}/api/tags", timeout=4)
        if r.status_code == 200:
            ollama_modelos = [m.get("name", "") for m in r.json().get("models", [])]
            ollama_ok = bool(ollama_modelos)
    except Exception:
        pass
    creds = {c.proveedor: bool(c.secreto_cifrado)
             for c in db.query(M.Credential).filter_by(user_id=u.id).all()}
    groq = bool(settings.GROQ_API_KEY) or creds.get("groq", False)
    if ollama_ok:
        recomendado = "ollama"
    elif groq:
        recomendado = "groq"
    elif creds.get("openai"):
        recomendado = "openai"
    elif creds.get("anthropic"):
        recomendado = "anthropic"
    else:
        recomendado = "demo"
    return {"ollama": {"ok": ollama_ok, "modelos": ollama_modelos},
            "groq": groq, "openai": creds.get("openai", False),
            "anthropic": creds.get("anthropic", False),
            "recomendado": recomendado, "demo": recomendado == "demo"}


@r_arch.get("")
def listar_archivos(prefijo: str = "", ruta: str = "", tarea_id: int | None = None,
                    db: Session = Depends(get_db), u=Depends(usuario_actual)):
    """Lista archivos del workspace indicado (explorador y @menciones). Límite 500."""
    from app.infraestructura.herramientas import Herramientas
    try:
        root = _raiz(db, u, ruta, tarea_id)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(403, str(exc))
    return {"prefijo": prefijo, "ruta": root, "archivos": Herramientas(root).listar(prefijo)[:500]}


def _raiz(db: Session, u, ruta: str = "", tarea_id: int | None = None) -> str:
    """Resuelve la carpeta de trabajo: ruta explícita > tarea/proyecto > defecto."""
    from app.infraestructura.herramientas import Herramientas
    if (ruta or "").strip():
        return Herramientas.validar_raiz(ruta)
    if tarea_id:
        t = db.query(M.TaskSession).filter_by(id=tarea_id, user_id=u.id).first()
        if not t:
            raise HTTPException(404, "Tarea no encontrada")
        root = (getattr(t, "ruta", "") or "").strip()
        if not root and t.project_id:
            proj = db.get(M.Project, t.project_id)
            root = (getattr(proj, "ruta", "") or "").strip() if proj else ""
        if root:
            return Herramientas.validar_raiz(root)
    return settings.WORKSPACE


@r_arch.get("/leer")
def leer_archivo_api(path: str, ruta: str = "", tarea_id: int | None = None,
                     db: Session = Depends(get_db), u=Depends(usuario_actual)):
    """Devuelve el contenido de un archivo para editarlo (el editor de código)."""
    from app.infraestructura.herramientas import Herramientas
    try:
        h = Herramientas(_raiz(db, u, ruta, tarea_id))
        texto, tipo = h.leer_documento(path, limite=200000)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(403, str(exc))
    if tipo == "binario":
        raise HTTPException(400, f"No editable como texto: {texto}")
    if tipo == "ausente":
        raise HTTPException(404, texto)
    return {"path": path, "contenido": texto, "tipo": tipo}


@r_arch.put("/guardar")
def guardar_archivo(d: S.GuardarArchivoIn, db: Session = Depends(get_db),
                    u=Depends(usuario_actual)):
    """Guarda lo editado manualmente (entra al historial: /undo también lo revierte)."""
    from app.infraestructura.herramientas import Herramientas
    try:
        h = Herramientas(_raiz(db, u, d.ruta, d.tarea_id))
        diff = h.modificar_archivo(d.path.strip(), d.contenido)
    except (ValueError, PermissionError, FileNotFoundError) as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "path": d.path, "diff": diff[:6000]}


@r_arch.post("/subir")
async def subir_documento(archivo: UploadFile = File(...), ruta: str = "",
                          db: Session = Depends(get_db), u=Depends(usuario_actual)):
    """Sube un documento (PDF/DOCX/TXT/…) al workspace para usarlo como contexto (@)."""
    from app.infraestructura.herramientas import Herramientas
    data = await archivo.read()
    try:
        h = Herramientas(Herramientas.validar_raiz(ruta) if ruta.strip() else None)
        nombre = h.guardar_bytes(archivo.filename or "archivo", data)
        texto, tipo = h.leer_documento(nombre)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(400, str(exc))
    return {"path": nombre, "tipo": tipo, "chars": len(texto),
            "vista_previa": texto[:500]}


@r_vista.get("/{tid}/{ruta:path}")
def vista_previa(tid: int, ruta: str, token: str = "", db: Session = Depends(get_db)):
    """Sirve archivos del workspace de la tarea (para ver el frontend generado).

    El token va por query porque un <iframe> no puede mandar headers.
    Sin `ruta` o con directorio → index.html.
    """
    from app.infraestructura.herramientas import Herramientas
    uid = leer_token(token)
    u = db.get(M.User, uid) if uid else None
    if not u:
        raise HTTPException(401, "token inválido")
    t = db.query(M.TaskSession).filter_by(id=tid, user_id=u.id).first()
    if not t:
        raise HTTPException(404, "Tarea no encontrada")
    root = (getattr(t, "ruta", "") or "").strip()
    if not root and t.project_id:
        proj = db.get(M.Project, t.project_id)
        root = (getattr(proj, "ruta", "") or "").strip() if proj else ""
    try:
        h = Herramientas(Herramientas.validar_raiz(root) if root else None)
        p = h._ruta_segura(ruta or "index.html")
    except (ValueError, PermissionError):
        raise HTTPException(403, "Ruta no permitida")
    if p.is_dir():
        p = p / "index.html"
    if not p.is_file():
        raise HTTPException(404, "Aún no generado — pide al agente crear index.html en la carpeta")
    return FileResponse(str(p))


@r_auth.post("/registro", response_model=S.TokenOut)
def registro(d: S.RegistroIn, db: Session = Depends(get_db)):
    if db.query(M.User).filter_by(email=d.email).first():
        raise HTTPException(400, "Email ya registrado")
    u = M.User(email=d.email, password_hash=hash_password(d.password))
    db.add(u); db.commit(); db.refresh(u)
    return S.TokenOut(access_token=crear_token(u.id))


@r_auth.post("/login", response_model=S.TokenOut)
def login(d: S.LoginIn, db: Session = Depends(get_db)):
    u = db.query(M.User).filter_by(email=d.email).first()
    if not u or not verificar_password(d.password, u.password_hash):
        raise HTTPException(401, "Credenciales inválidas")
    return S.TokenOut(access_token=crear_token(u.id))


@r_proy.post("")
def crear_proyecto(d: S.ProyectoIn, db: Session = Depends(get_db), u=Depends(usuario_actual)):
    p = M.Project(user_id=u.id, nombre=d.nombre, descripcion=d.descripcion, ruta=d.ruta or "")
    db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id, "nombre": p.nombre, "descripcion": p.descripcion, "ruta": p.ruta}


@r_proy.get("")
def listar_proyectos(db: Session = Depends(get_db), u=Depends(usuario_actual)):
    return [{"id": p.id, "nombre": p.nombre, "descripcion": p.descripcion,
             "ruta": getattr(p, "ruta", "") or ""}
            for p in db.query(M.Project).filter_by(user_id=u.id).all()]


@r_cred.post("")
def guardar_credencial(d: S.CredencialIn, db: Session = Depends(get_db), u=Depends(usuario_actual)):
    # NUNCA loguear d.api_key. Solo se guarda cifrada.
    cifrada = crypto.cifrar(d.api_key) if d.api_key else ""
    c = M.Credential(user_id=u.id, proveedor=d.proveedor, etiqueta=d.etiqueta, secreto_cifrado=cifrada)
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "proveedor": c.proveedor, "etiqueta": c.etiqueta, "tiene_key": bool(cifrada)}


@r_cred.get("")
def listar_credenciales(db: Session = Depends(get_db), u=Depends(usuario_actual)):
    # Jamás se devuelve el secreto, solo metadatos.
    return [{"id": c.id, "proveedor": c.proveedor, "etiqueta": c.etiqueta,
             "tiene_key": bool(c.secreto_cifrado)}
            for c in db.query(M.Credential).filter_by(user_id=u.id).all()]


@r_tareas.post("")
def crear_tarea(d: S.TareaIn, db: Session = Depends(get_db), u=Depends(usuario_actual)):
    from app.infraestructura.herramientas import Herramientas
    ruta = (d.ruta or "").strip()
    if not ruta and d.project_id:
        proj = db.query(M.Project).filter_by(id=d.project_id, user_id=u.id).first()
        ruta = (getattr(proj, "ruta", "") or "") if proj else ""
    if ruta:
        ruta = Herramientas.validar_raiz(ruta)  # rechaza carpetas del sistema
    t = M.TaskSession(user_id=u.id, project_id=d.project_id, objetivo=d.objetivo,
                      estado="pendiente", modelo=d.modelo, ruta=ruta)
    db.add(t); db.commit(); db.refresh(t)
    archivos = d.archivos
    db.add(M.TaskEvent(session_id=t.id, tipo="tarea_creada",
                       datos={"objetivo": d.objetivo, "archivos": archivos,
                              "modelo": d.modelo, "ruta": ruta}))
    db.commit()
    return {"id": t.id, "estado": t.estado,
            "ws_url": f"/ws/tareas/{t.id}",
            "archivos": archivos, "ruta": ruta}


@r_tareas.get("")
def historial(db: Session = Depends(get_db), u=Depends(usuario_actual)):
    ts = db.query(M.TaskSession).filter_by(user_id=u.id).order_by(M.TaskSession.id.desc()).all()
    return [{"id": t.id, "objetivo": t.objetivo, "estado": t.estado,
             "modelo": t.modelo, "resumen": t.resumen,
             "project_id": t.project_id, "creado": t.creado.isoformat() if t.creado else None}
            for t in ts]


@r_tareas.get("/{tid}")
def detalle_tarea(tid: int, db: Session = Depends(get_db), u=Depends(usuario_actual)):
    t = db.query(M.TaskSession).filter_by(id=tid, user_id=u.id).first()
    if not t:
        raise HTTPException(404, "Tarea no encontrada")
    evs = db.query(M.TaskEvent).filter_by(session_id=tid).order_by(M.TaskEvent.id).all()
    return {"id": t.id, "objetivo": t.objetivo, "estado": t.estado,
            "modelo": t.modelo, "resumen": t.resumen,
            "ruta": getattr(t, "ruta", "") or "",
            "eventos": [{"tipo": e.tipo, "datos": e.datos} for e in evs]}


@r_tareas.post("/{tid}/continuar")
def continuar_tarea(tid: int, d: S.ContinuarIn, db: Session = Depends(get_db),
                    u=Depends(usuario_actual)):
    """Seguir escribiendo en una tarea terminada: crea una sesión nueva que
    hereda proyecto, modelo, carpeta y el resumen anterior como contexto."""
    t = db.query(M.TaskSession).filter_by(id=tid, user_id=u.id).first()
    if not t:
        raise HTTPException(404, "Tarea no encontrada")
    contexto = (t.resumen or "")[:2000]
    nt = M.TaskSession(user_id=u.id, project_id=t.project_id, objetivo=d.texto,
                       estado="pendiente", modelo=t.modelo,
                       ruta=getattr(t, "ruta", "") or "")
    db.add(nt); db.commit(); db.refresh(nt)
    db.add(M.TaskEvent(session_id=nt.id, tipo="tarea_creada",
                       datos={"objetivo": d.texto, "archivos": [], "modelo": nt.modelo,
                              "ruta": nt.ruta, "continuacion_de": tid,
                              "contexto_previo": contexto}))
    db.commit()
    return {"id": nt.id, "estado": nt.estado, "ws_url": f"/ws/tareas/{nt.id}",
            "continuacion_de": tid}


@r_tareas.delete("/{tid}")
def borrar_tarea(tid: int, db: Session = Depends(get_db), u=Depends(usuario_actual)):
    t = db.query(M.TaskSession).filter_by(id=tid, user_id=u.id).first()
    if not t:
        raise HTTPException(404, "Tarea no encontrada")
    if t.estado == "en_curso":
        raise HTTPException(409, "La tarea está en curso: usa /stop antes de borrarla")
    db.delete(t)  # los eventos se borran en cascada
    db.commit()
    return {"ok": True, "id": tid}
