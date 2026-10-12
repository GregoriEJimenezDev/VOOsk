"""Comandos especiales `/...` y menciones `@archivo`.

Se escriben en la misma barra de instrucciones en vivo y viajan por el
mismo WebSocket. El parser es puro (sin FastAPI) para poder testearlo.

Comandos:
  /undo [n] [@archivo]  revierte las últimas n escrituras (default 1)
  /wait                 pausa al agente entre pasos
  /resume               reanuda la tarea pausada
  /stop                 cancela la tarea
  /approve [n]          aprueba el paso pendiente n
  /status               resume el estado actual
  /files [prefijo]      lista archivos del workspace
  /help                 muestra esta ayuda

Menciones: cualquier texto con @ruta lo adjunta como contexto
(ej: "@main.py explica este archivo").
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

MENCION = re.compile(r"@([\w\-./\\]+)")

ALIAS = {
    "undo": "undo", "deshacer": "undo",
    "wait": "wait", "pausa": "wait", "pausar": "wait", "espera": "wait",
    "resume": "resume", "continua": "resume", "continuar": "resume",
    "sigue": "resume", "go": "resume",
    "stop": "stop", "cancelar": "stop", "cancela": "stop", "para": "stop",
    "approve": "approve", "aprobar": "approve", "aprueba": "approve",
    "status": "status", "estado": "status",
    "files": "files", "archivos": "files", "ls": "files",
    "help": "help", "ayuda": "help",
}

AYUDA = [
    ("/undo [n] [@archivo]", "revierte las últimas n modificaciones"),
    ("/wait · /resume", "pausa y reanuda al agente"),
    ("/stop", "cancela la tarea"),
    ("/approve [n]", "aprueba un paso pendiente"),
    ("/status", "muestra el estado actual"),
    ("/files [prefijo]", "lista archivos del workspace"),
    ("@archivo", "adjunta un archivo como contexto"),
    ("/help", "muestra esta ayuda"),
]


@dataclass
class Mensaje:
    es_comando: bool = False
    comando: str = ""          # nombre canónico o ""
    args: list[str] = field(default_factory=list)
    menciones: list[str] = field(default_factory=list)  # @archivos
    texto: str = ""            # texto original


def parsear(texto: str) -> Mensaje:
    t = (texto or "").strip()
    m = Mensaje(texto=texto or "")
    m.menciones = [x.strip("./") for x in MENCION.findall(t)]
    if t.startswith("/"):
        partes = t.split()
        nombre = partes[0][1:].lower()
        m.es_comando = True
        m.comando = ALIAS.get(nombre, "desconocido")
        m.args = partes[1:]
    return m


def numero_arg(args: list[str], default: int = 1) -> int:
    for a in args:
        if a.lstrip("@").isdigit():
            return max(1, int(a.lstrip("@")))
    return default


def archivo_arg(args: list[str], menciones: list[str]) -> str | None:
    for a in args:
        if "." in a and not a.isdigit():
            return a.lstrip("@")
    return menciones[0] if menciones else None
