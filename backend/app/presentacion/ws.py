"""WebSocket por sesión de tarea: eventos incrementales en tiempo real.

Conectar:  ws://localhost:8000/ws/tareas/{id}?token=JWT
El servidor ejecuta el orquestador y emite:
plan_generado, paso_iniciado, herramienta_usada, archivo_leido,
archivo_modificado (diff), comando_ejecutado (salida),
accion_requiere_aprobacion, paso_completado, tarea_finalizada,
instruccion_usuario, instruccion_aplicada

El cliente puede enviar: {"accion":"aprobar","numero":N} y
{"accion":"instruir","texto":"..."} para dar instrucciones en vivo.
"""
from __future__ import annotations
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pathlib import Path
from app.config import settings
from app.infraestructura.db.sesion import SessionLocal
from app.infraestructura.db import modelos as M
from app.infraestructura.seguridad import crypto
from app.infraestructura.seguridad.redactar import redactar
from app.infraestructura.adapters import construir_adapter, adapter_automatico, FakeAdapter
from app.infraestructura.herramientas import Herramientas
from app.aplicacion.comandos import parsear, numero_arg, archivo_arg, AYUDA
from app.aplicacion.orquestador import OrquestadorAgente, TareaCancelada
from app.presentacion.deps import usuario_ws

router = APIRouter()


class Hub:
    """Broadcast a todos los sockets de una misma tarea."""
    def __init__(self):
        self.salas: dict[int, set[WebSocket]] = {}

    def unir(self, tid: int, ws: WebSocket):
        self.salas.setdefault(tid, set()).add(ws)

    def salir(self, tid: int, ws: WebSocket):
        self.salas.get(tid, set()).discard(ws)

    async def broadcast(self, tid: int, tipo: str, datos: dict):
        msg = json.dumps({"tipo": tipo, "datos": redactar(datos)}, ensure_ascii=False)
        for ws in list(self.salas.get(tid, set())):
            try:
                await ws.send_text(msg)
            except Exception:
                pass


hub = Hub()
_en_ejecucion: set[int] = set()
COLAS: dict[int, list[str]] = {}    # instrucciones en vivo por tarea
CONTROLES: dict[int, dict] = {}     # {"pausa": bool, "cancelar": bool} por tarea
HERRAMIENTAS = Herramientas()       # compat: instancia por defecto (ver herramientas_de)
_HERRAMIENTAS: dict[str, Herramientas] = {}  # root -> instancia (conserva historial /undo)
RUTAS: dict[int, str] = {}                   # tid -> carpeta de trabajo resuelta


def herramientas_de(tid: int | None = None) -> Herramientas:
    """Una instancia por carpeta: el historial de /undo no se mezcla entre proyectos."""
    root = (RUTAS.get(tid or -1, "") or settings.WORKSPACE)
    key = str(Path(root).expanduser().resolve())
    if key not in _HERRAMIENTAS:
        _HERRAMIENTAS[key] = Herramientas(key)
    return _HERRAMIENTAS[key]


def _guardar(tid: int, tipo: str, datos: dict):
    db = SessionLocal()
    try:
        # redactar: ni claves ni tokens quedan en BD
        db.add(M.TaskEvent(session_id=tid, tipo=tipo, datos=redactar(datos)))
        db.commit()
    finally:
        db.close()


async def _manejar_accion(tid: int, data: dict):
    """Rutea mensajes del cliente: aprobar, instruir (texto, /comandos, @archivos)."""
    accion = data.get("accion")
    if accion == "aprobar":
        _guardar(tid, "aprobacion_humana", {"numero": data.get("numero")})
        await hub.broadcast(tid, "aprobacion_humana", {"numero": data.get("numero")})
        return
    if accion != "instruir":
        return
    texto = str(data.get("texto", "")).strip()[:2000]
    if not texto:
        return
    # No aceptar instrucciones en sesiones ya terminadas (evita hablarle a una tarea muerta)
    db0 = SessionLocal()
    try:
        t0 = db0.get(M.TaskSession, tid)
        if not t0 or (t0.estado or "") not in ("pendiente", "en_curso"):
            await hub.broadcast(tid, "error", {"msg": "Esta sesión ya terminó. Crea una tarea nueva con ＋ Nueva tarea."})
            return
    finally:
        db0.close()
    msg = parsear(texto)
    if msg.es_comando:
        await _ejecutar_comando(tid, msg)
        return
    # Texto normal (+ posibles @menciones como contexto adjunto)
    adjuntos: list[dict] = []
    extra = ""
    for path in msg.menciones[:3]:
        try:
            contenido = herramientas_de(tid).leer_archivo(path)
            extra += f"\n\n--- contexto @{path} ---\n{contenido[:4000]}"
            adjuntos.append({"path": path, "chars": len(contenido)})
        except PermissionError:
            adjuntos.append({"path": path, "error": "fuera del workspace"})
    enriquecido = texto + extra
    _guardar(tid, "instruccion_usuario", {"texto": texto, "adjuntos": adjuntos})
    COLAS.setdefault(tid, []).append(enriquecido)
    await hub.broadcast(tid, "instruccion_usuario", {"texto": texto, "adjuntos": adjuntos})


async def _ejecutar_comando(tid: int, msg):
    c, args = msg.comando, msg.args
    if c == "undo":
        n = numero_arg(args)
        path = archivo_arg(args, msg.menciones)
        try:
            for p, diff in herramientas_de(tid).deshacer(path, n):
                datos = {"path": p, "diff": diff[:6000]}
                _guardar(tid, "archivo_restaurado", datos)
                await hub.broadcast(tid, "archivo_restaurado", datos)
        except (LookupError, PermissionError) as exc:
            await hub.broadcast(tid, "error", {"msg": str(exc)})
    elif c == "wait":
        CONTROLES.setdefault(tid, {})["pausa"] = True
        _guardar(tid, "tarea_pausada", {})
        await hub.broadcast(tid, "tarea_pausada", {})
    elif c == "resume":
        CONTROLES.setdefault(tid, {})["pausa"] = False
        _guardar(tid, "tarea_reanudada", {})
        await hub.broadcast(tid, "tarea_reanudada", {})
    elif c == "stop":
        CONTROLES.setdefault(tid, {})["cancelar"] = True
        CONTROLES[tid]["pausa"] = False
        await hub.broadcast(tid, "tarea_cancelada", {})
    elif c == "approve":
        num = data_num(args)
        _guardar(tid, "aprobacion_humana", {"numero": num})
        await hub.broadcast(tid, "aprobacion_humana", {"numero": num})
    elif c == "status":
        datos = _estado_actual(tid)
        _guardar(tid, "estado_actual", datos)
        await hub.broadcast(tid, "estado_actual", datos)
    elif c == "files":
        pref = args[0] if args else ""
        datos = {"prefijo": pref, "archivos": herramientas_de(tid).listar(pref)[:100],
                 "ruta": RUTAS.get(tid, "")}
        _guardar(tid, "lista_archivos", datos)
        await hub.broadcast(tid, "lista_archivos", datos)
    elif c == "help":
        datos = {"comandos": [{"cmd": k, "desc": v} for k, v in AYUDA]}
        await hub.broadcast(tid, "ayuda", datos)
    else:
        await hub.broadcast(tid, "error", {"msg": f"Comando desconocido. Prueba /help"})


def data_num(args: list[str]) -> int | None:
    for a in args:
        if a.lstrip("@").isdigit():
            return int(a.lstrip("@"))
    return None


def _estado_actual(tid: int) -> dict:
    db = SessionLocal()
    try:
        tarea = db.get(M.TaskSession, tid)
        evs = db.query(M.TaskEvent).filter_by(session_id=tid).all()
        tipos = [e.tipo for e in evs]
        plan = next((e.datos.get("plan") for e in evs if e.tipo == "plan_generado"), None)
        ultimo_paso = next((e.datos.get("numero") for e in reversed(evs)
                            if e.tipo == "paso_iniciado"), None)
        return {
            "estado": tarea.estado if tarea else "?",
            "modelo": tarea.modelo if tarea else "?",
            "total_pasos": len(plan["pasos"]) if plan else 0,
            "pasos_completados": tipos.count("paso_completado"),
            "paso_actual": ultimo_paso,
            "eventos": len(evs),
            "pausado": bool(CONTROLES.get(tid, {}).get("pausa")),
            "ruta": RUTAS.get(tid, ""),
        }
    finally:
        db.close()
COLAS: dict[int, list[str]] = {}  # instrucciones en vivo por tarea


@router.websocket("/ws/tareas/{tid}")
async def ws_tarea(websocket: WebSocket, tid: int):
    await websocket.accept()
    db = SessionLocal()
    try:
        user = usuario_ws(websocket, db)
        if not user:
            await websocket.send_text(json.dumps({"tipo": "error", "datos": {"msg": "token inválido"}}))
            await websocket.close()
            return
        tarea = db.query(M.TaskSession).filter_by(id=tid, user_id=user.id).first()
        if not tarea:
            await websocket.send_text(json.dumps({"tipo": "error", "datos": {"msg": "tarea no encontrada"}}))
            await websocket.close()
            return
        hub.unir(tid, websocket)
        # Reenviar historial al recién conectado (transparencia total)
        evs = db.query(M.TaskEvent).filter_by(session_id=tid).order_by(M.TaskEvent.id).all()
        for e in evs:
            await websocket.send_text(json.dumps({"tipo": e.tipo, "datos": e.datos}, ensure_ascii=False))

        if tid not in _en_ejecucion and tarea.estado in ("pendiente",):
            _en_ejecucion.add(tid)
            asyncio.create_task(_correr(tid))
        # Mantener vivo: aprobar, instruir, /comandos y @menciones
        while True:
            try:
                raw = await websocket.receive_text()
                await _manejar_accion(tid, json.loads(raw))
            except WebSocketDisconnect:
                break
            except Exception:
                pass
    finally:
        hub.salir(tid, websocket)
        db.close()


async def _correr(tid: int):
    db = SessionLocal()
    try:
        tarea = db.get(M.TaskSession, tid)
        if not tarea:
            return
        tarea.estado = "en_curso"
        db.commit()

        async def emitir(tipo: str, datos: dict):
            d2 = SessionLocal()
            try:
                # Nunca persistir secretos (redactar) ni loguear claves
                d2.add(M.TaskEvent(session_id=tid, tipo=tipo, datos=redactar(datos)))
                d2.commit()
            finally:
                d2.close()
            await hub.broadcast(tid, tipo, datos)

        # Resolver adapter: BYOK del usuario o detección automática gratuita
        # (Ollama local con modelos > Groq en la nube > demo).
        d = db.query(M.Credential).filter_by(user_id=tarea.user_id, proveedor=tarea.modelo).first()
        key = crypto.descifrar(d.secreto_cifrado) if d and d.secreto_cifrado else ""
        try:
            if (tarea.modelo or "gratuito").lower() in ("gratuito", "auto"):
                g = db.query(M.Credential).filter_by(user_id=tarea.user_id, proveedor="groq").first()
                gkey = crypto.descifrar(g.secreto_cifrado) if g and g.secreto_cifrado else ""
                adapter = await adapter_automatico(gkey)
            else:
                adapter = construir_adapter(tarea.modelo, key)
        except ValueError as exc:
            await emitir("tarea_finalizada", {"resumen": f"Error de configuración: {exc}"})
            tarea.estado = "fallida"
            db.commit()
            return
        if isinstance(adapter, FakeAdapter):
            await emitir("modelo_demo", {
                "mensaje": "Sin modelo de IA conectado: estoy en modo demo.",
                "pasos": ["Abre la app de Ollama en tu PC (gratis, local) y reintenta, o",
                          "crea una key gratuita en console.groq.com y pégala en BYOK → Groq."],
            })

        # Archivos de contexto guardados en tarea_creada
        ev0 = db.query(M.TaskEvent).filter_by(session_id=tid, tipo="tarea_creada").first()
        archivos = (ev0.datos.get("archivos", []) if ev0 else [])
        # Carpeta de trabajo: tarea > proyecto > workspace por defecto
        ruta = (getattr(tarea, "ruta", "") or "").strip()
        if not ruta and tarea.project_id:
            proj = db.get(M.Project, tarea.project_id)
            ruta = (getattr(proj, "ruta", "") or "").strip() if proj else ""
        if ruta:
            ruta = Herramientas.validar_raiz(ruta)
        RUTAS[tid] = ruta or settings.WORKSPACE
        orch = OrquestadorAgente(adapter, herramientas_de(tid), emitir)
        bandeja = COLAS.setdefault(tid, [])
        # Contexto heredado de una continuación (/tareas/{id}/continuar)
        if ev0 and ev0.datos.get("contexto_previo"):
            bandeja.insert(0, f"Contexto de la tarea anterior #{ev0.datos.get('continuacion_de')}: "
                              f"{ev0.datos['contexto_previo']}")
        control = CONTROLES.setdefault(tid, {"pausa": False, "cancelar": False})
        try:
            resumen = await orch.ejecutar(tarea.objetivo, archivos, bandeja, control)
        except TareaCancelada:
            _guardar(tid, "tarea_finalizada", {"resumen": "⛔ Tarea cancelada por el usuario.",
                                               "cancelada": True})
            await hub.broadcast(tid, "tarea_finalizada",
                                {"resumen": "⛔ Tarea cancelada por el usuario.", "cancelada": True})
            tarea.resumen = "Cancelada por el usuario."
            tarea.estado = "cancelada"
            db.commit()
            return
        tarea.resumen = resumen[:8000]
        tarea.estado = "completada"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        try:
            await hub.broadcast(tid, "tarea_finalizada", {"resumen": f"ERROR: {exc}"})
            t = db.get(M.TaskSession, tid)
            if t:
                t.estado = "fallida"
                db.commit()
        except Exception:
            pass
    finally:
        _en_ejecucion.discard(tid)
        COLAS.pop(tid, None)
        CONTROLES.pop(tid, None)
        RUTAS.pop(tid, None)
        db.close()
