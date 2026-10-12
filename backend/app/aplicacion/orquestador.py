"""Orquestador de agentes desacoplado.

Recibe un ModelAdapter + herramientas + un emisor de eventos (callback).
No conoce FastAPI ni WebSockets: solo llama a `emitir(tipo, datos)`.
La capa de presentación conecta ese callback al WebSocket.
"""
from __future__ import annotations
import asyncio
from typing import Awaitable, Callable

from app.dominio.entidades import Plan, PlanPaso

Emitir = Callable[[str, dict], Awaitable[None]]


class TareaCancelada(Exception):
    """El usuario pidió /stop: se aborta entre pasos."""


class OrquestadorAgente:
    def __init__(self, adapter, herramientas, emitir: Emitir):
        self.adapter = adapter
        self.herramientas = herramientas
        self.emitir = emitir

    async def ejecutar(self, objetivo: str, contexto_archivos: list[str] | None = None,
                       bandeja: list[str] | None = None,
                       control: dict | None = None) -> str:
        """bandeja: lista compartida donde la capa de presentación deposita
        instrucciones del usuario que llegan EN VIVO. Se aplican desde el
        siguiente paso sin reiniciar la tarea.
        control: dict compartido {"pausa": bool, "cancelar": bool} (/wait, /stop)."""
        contexto_archivos = contexto_archivos or []
        plan = await self._generar_plan(objetivo, contexto_archivos)
        await self.emitir("plan_generado", {"plan": plan.to_dict(), "modelo": self.adapter.nombre})

        resultado_final: list[str] = []
        extras: list[str] = []  # instrucciones en vivo acumuladas
        ctrl = control or {}
        for paso in plan.pasos:
            while ctrl.get("pausa") and not ctrl.get("cancelar"):
                await asyncio.sleep(0.5)  # /wait: quieto entre pasos
            if ctrl.get("cancelar"):
                raise TareaCancelada()
            if bandeja:
                nuevas = list(bandeja)
                bandeja.clear()
                if nuevas:
                    extras.extend(nuevas)
                    await self.emitir("instruccion_aplicada",
                                      {"numero": paso.numero, "instrucciones": nuevas})
            ctx_extra = "\n".join(f"- {t}" for t in extras)
            await self.emitir("paso_iniciado", {"numero": paso.numero, "titulo": paso.titulo})
            try:
                salida = await self._ejecutar_paso(paso, objetivo, ctx_extra)
                resultado_final.append(f"Paso {paso.numero} ({paso.titulo}): {salida}")
                await self.emitir("paso_completado", {"numero": paso.numero, "resumen": salida[:2000]})
            except PermissionError as exc:  # requiere aprobación humana
                await self.emitir("accion_requiere_aprobacion",
                                  {"numero": paso.numero, "detalle": str(exc), "titulo": paso.titulo})
                resultado_final.append(f"Paso {paso.numero} PENDIENTE DE APROBACIÓN: {exc}")
            except Exception as exc:  # noqa: BLE001 - el agente debe seguir y reportar
                await self.emitir("paso_completado",
                                  {"numero": paso.numero, "resumen": f"ERROR: {exc}", "error": True})
                resultado_final.append(f"Paso {paso.numero} ERROR: {exc}")

        resumen = "\n".join(resultado_final)
        vivo = f"\n\nInstrucciones en vivo recibidas:\n{chr(10).join(extras)}" if extras else ""
        # Resumen final con el modelo (si falla, se usa el texto acumulado)
        try:
            cierre = await self.adapter.completar(
                "Eres un asistente de desarrollo. Resume el trabajo hecho de forma concisa.",
                f"Objetivo: {objetivo}\n\nResultados por paso:\n{resumen}{vivo}",
            )
        except Exception:
            cierre = resumen
        await self.emitir("tarea_finalizada", {"resumen": cierre})
        return cierre

    # ---- internos ----
    async def _generar_plan(self, objetivo: str, archivos: list[str]) -> Plan:
        prompt = (
            f"Objetivo del usuario: {objetivo}\n"
            f"Archivos de contexto: {', '.join(archivos) if archivos else 'ninguno'}\n\n"
            "Devuelve un plan numerado, una línea por paso, con formato:\n"
            "1. [leer_archivo|modificar_archivo|editar_archivo|ejecutar_comando|general] Título - descripción breve\n"
            "Usa modificar_archivo para crear archivos (cualquier extensión de texto: .html, .css, "
            ".js, .py, .json…) y editar_archivo para cambios puntuales en archivos existentes."
        )
        try:
            texto = await self.adapter.completar(
                "Eres un planificador de tareas de software. Responde SOLO con el plan numerado.",
                prompt,
            )
            pasos = self._parsear_plan(texto)
            if pasos:
                return Plan(objetivo=objetivo, pasos=pasos)
        except Exception:
            pass
        return self._plan_por_defecto(objetivo, archivos)

    @staticmethod
    def _parsear_plan(texto: str) -> list[PlanPaso]:
        import re
        pasos: list[PlanPaso] = []
        for line in texto.strip().splitlines():
            m = re.match(r"\s*(\d+)[.)\-]\s*(?:\[(\w+)\])?\s*(.+)", line)
            if not m:
                continue
            num = int(m.group(1))
            herr = (m.group(2) or "general").lower()
            resto = m.group(3).strip()
            if " - " in resto:
                titulo, desc = resto.split(" - ", 1)
            else:
                titulo, desc = resto[:60], resto
            pasos.append(PlanPaso(numero=num, titulo=titulo.strip(), descripcion=desc.strip(), herramienta=herr))
        return pasos[:10]

    @staticmethod
    def _parsear_buscar_reemplazo(texto: str) -> tuple[str, str]:
        if "BUSCAR:" not in texto or "REEMPLAZO:" not in texto:
            raise ValueError("El modelo no devolvió bloques BUSCAR:/REEMPLAZO:")
        _, resto = texto.split("BUSCAR:", 1)
        buscar, reemplazo = resto.split("REEMPLAZO:", 1)
        buscar, reemplazo = buscar.strip(), reemplazo.strip()
        if not buscar or not reemplazo:
            raise ValueError("Bloques BUSCAR/REEMPLAZO vacíos")
        return buscar, reemplazo

    @staticmethod
    def _plan_por_defecto(objetivo: str, archivos: list[str]) -> Plan:
        pasos = [
            PlanPaso(1, "Analizar objetivo", objetivo[:120], "general"),
        ]
        n = 2
        for a in (archivos or [])[:3]:
            pasos.append(PlanPaso(n, f"Leer {a}", f"Leer el archivo {a} como contexto", "leer_archivo"))
            n += 1
        pasos.append(PlanPaso(n, "Ejecutar y concluir", "Ejecutar comprobaciones y resumir", "general"))
        return Plan(objetivo=objetivo, pasos=pasos)

    async def _ejecutar_paso(self, paso: PlanPaso, objetivo: str, contexto_extra: str = "") -> str:
        h = paso.herramienta
        ctx = (f"\n\nInstrucciones del usuario en vivo (prioridad alta):\n{contexto_extra}"
               if contexto_extra else "")
        await self.emitir("herramienta_usada", {"numero": paso.numero, "herramienta": h, "titulo": paso.titulo})
        if h == "leer_archivo":
            # la herramienta infiere el path del título/descripción
            path = self.herramientas.extraer_path(paso.titulo + " " + paso.descripcion)
            contenido = await asyncio.to_thread(self.herramientas.leer_archivo, path)
            es_doc = path.lower().endswith((".pdf", ".docx"))
            await self.emitir("archivo_leido", {"numero": paso.numero, "path": path,
                                                "contenido": contenido[:4000],
                                                "documento": es_doc})
            # pedir al modelo un análisis breve del archivo
            analisis = await self.adapter.completar(
                "Eres un asistente de código. Analiza brevemente.",
                f"Archivo {path}:\n{contenido[:3000]}\n\nObjetivo: {objetivo}{ctx}",
            )
            return f"Leído {path} ({len(contenido)} chars). Análisis: {analisis[:500]}"
        if h == "modificar_archivo":
            path = self.herramientas.extraer_path(paso.titulo + " " + paso.descripcion)
            propuesta = await self.adapter.completar(
                "Eres un asistente de código. Propón el contenido completo del archivo.",
                f"Objetivo: {objetivo}\nPaso: {paso.titulo} - {paso.descripcion}\n"
                f"Devuelve SOLO el nuevo contenido del archivo {path}.{ctx}",
            )
            diff = await asyncio.to_thread(self.herramientas.modificar_archivo, path, propuesta)
            await self.emitir("archivo_modificado", {"numero": paso.numero, "path": path, "diff": diff[:6000]})
            return f"Modificado {path}. Diff de {len(diff)} chars."
        if h == "editar_archivo":
            path = self.herramientas.extraer_path(paso.titulo + " " + paso.descripcion)
            propuesta = await self.adapter.completar(
                "Eres un asistente de código. Devuelve bloques BUSCAR y REEMPLAZO exactos.",
                f"Objetivo: {objetivo}\nArchivo: {path}\n"
                f"Paso: {paso.titulo} - {paso.descripcion}{ctx}\n\n"
                "Formato exacto:\nBUSCAR:\n<fragmento exacto actual del archivo>\n"
                "REEMPLAZO:\n<fragmento nuevo>",
            )
            buscar, reemplazo = self._parsear_buscar_reemplazo(propuesta)
            diff = await asyncio.to_thread(self.herramientas.editar_fragmento, path, buscar, reemplazo)
            await self.emitir("archivo_modificado", {"numero": paso.numero, "path": path, "diff": diff[:6000]})
            return f"Editado {path}. Diff de {len(diff)} chars."
        if h == "ejecutar_comando":
            cmd = self.herramientas.extraer_comando(paso.titulo + " " + paso.descripcion)
            salida = await asyncio.to_thread(self.herramientas.ejecutar_comando, cmd)
            await self.emitir("comando_ejecutado", {"numero": paso.numero, "comando": cmd,
                                                    "salida": salida[:6000]})
            return f"Comando '{cmd}' ejecutado. Salida: {salida[:500]}"
        # general: razonamiento del modelo
        texto = await self.adapter.completar(
            "Eres un agente de desarrollo transparente. Explica qué harías en este paso.",
            f"Objetivo: {objetivo}\nPaso {paso.numero}: {paso.titulo} - {paso.descripcion}{ctx}",
        )
        return texto[:1000]
