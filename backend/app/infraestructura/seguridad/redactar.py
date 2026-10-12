"""Tacha secretos (API keys, tokens) en cualquier estructura de datos.

Se aplica a los eventos ANTES de guardarlos en BD y de emitirlos por
WebSocket: aunque un archivo leído o una salida de comando contenga una
clave, nunca queda persistida ni viaja al frontend/CLI. Tampoco se loguea.
"""
from __future__ import annotations
import re

_PATRONES = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),            # OpenAI
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),        # Anthropic
    re.compile(r"gsk_[A-Za-z0-9_\-]{8,}"),           # Groq
    re.compile(r"ghp_[A-Za-z0-9]{8,}"),              # GitHub
    re.compile(r"xox[bap]-[A-Za-z0-9\-]{8,}"),       # Slack
    re.compile(r"(?i)(api[_-]?key|apikey|secret|passwd|password|token)\s*[:=]\s*['\"]?[\w\-.~+/=]{8,}"),
    re.compile(r"Bearer\s+[\w\-.~+/=]{8,}"),
]

REEMPLAZO = "[SECRETO]"


def _texto(s: str) -> str:
    for p in _PATRONES:
        s = p.sub(REEMPLAZO, s)
    return s


def redactar(obj):
    if isinstance(obj, str):
        return _texto(obj)
    if isinstance(obj, dict):
        return {k: redactar(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redactar(v) for v in obj]
    return obj
