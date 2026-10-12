"""Puertos (interfaces) del dominio. El núcleo solo depende de esto (SOLID/DIP)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class ModelAdapter(ABC):
    """Adapter/Strategy común. Añadir un proveedor = nueva subclase, sin tocar el núcleo."""

    nombre: str = "base"

    @abstractmethod
    async def completar(self, prompt_sistema: str, prompt_usuario: str,
                        historial: list[dict] | None = None) -> str:
        """Devuelve texto del modelo."""
        raise NotImplementedError

    def requiere_api_key(self) -> bool:
        return False
