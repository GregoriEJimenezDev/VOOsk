"""Entidades de dominio (puras, sin dependencias de infra)."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class EstadoTarea(str, Enum):
    PENDIENTE = "pendiente"
    EN_CURSO = "en_curso"
    ESPERANDO_APROBACION = "esperando_aprobacion"
    COMPLETADA = "completada"
    FALLIDA = "fallida"


class TipoEvento(str, Enum):
    PLAN_GENERADO = "plan_generado"
    PASO_INICIADO = "paso_iniciado"
    HERRAMIENTA_USADA = "herramienta_usada"
    ARCHIVO_LEIDO = "archivo_leido"
    ARCHIVO_MODIFICADO = "archivo_modificado"
    COMANDO_EJECUTADO = "comando_ejecutado"
    ACCION_REQUIERE_APROBACION = "accion_requiere_aprobacion"
    PASO_COMPLETADO = "paso_completado"
    TAREA_FINALIZADA = "tarea_finalizada"


@dataclass
class PlanPaso:
    numero: int
    titulo: str
    descripcion: str
    herramienta: str = "general"  # leer_archivo | modificar_archivo | ejecutar_comando | general


@dataclass
class Plan:
    objetivo: str
    pasos: list[PlanPaso] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "objetivo": self.objetivo,
            "pasos": [p.__dict__ for p in self.pasos],
        }


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)
