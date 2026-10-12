"""Casos de uso: auth, proyectos, credenciales, tareas. Sin FastAPI ni SQL aquí."""
from __future__ import annotations
import uuid


def nuevo_id() -> str:
    return uuid.uuid4().hex[:12]
