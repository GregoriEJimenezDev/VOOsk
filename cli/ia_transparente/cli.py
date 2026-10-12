"""CLI `voosk`: consume la MISMA API REST + WebSocket que el frontend."""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path

import httpx
import typer
import websockets

app = typer.Typer(help="VOOsk — agentes con trazabilidad en tiempo real")
API = os.getenv("VOOSK_API", os.getenv("IA_API", "http://localhost:8000"))
CFG = Path.home() / ".ia_transparente.json"


def _token() -> str:
    return json.loads(CFG.read_text()).get("token", "") if CFG.exists() else ""


def _h() -> dict:
    return {"Authorization": f"Bearer {_token()}"} if _token() else {}


@app.command()
def login(email: str, password: str):
    r = httpx.post(f"{API}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    CFG.write_text(json.dumps({"token": r.json()["access_token"]}))
    typer.echo("OK: sesión guardada")


@app.command()
def registro(email: str, password: str):
    r = httpx.post(f"{API}/auth/registro", json={"email": email, "password": password})
    r.raise_for_status()
    CFG.write_text(json.dumps({"token": r.json()["access_token"]}))
    typer.echo("OK: usuario creado")


@app.command()
def iniciar(objetivo: str, modelo: str = "gratuito"):
    """Crea la tarea por REST y muestra los eventos del WebSocket en vivo."""
    r = httpx.post(f"{API}/tareas", json={"objetivo": objetivo, "modelo": modelo, "archivos": []},
                   headers=_h())
    r.raise_for_status()
    tid = r.json()["id"]
    typer.echo(f"Tarea #{tid} — mostrando ejecución en tiempo real…")
    asyncio.run(_ver_en_vivo(tid))


@app.command()
def ver(tarea_id: int):
    asyncio.run(_ver_en_vivo(tarea_id))


async def _ver_en_vivo(tid: int):
    ws_url = API.replace("http", "ws") + f"/ws/tareas/{tid}?token={_token()}"
    async with websockets.connect(ws_url) as ws:
        async for raw in ws:
            ev = json.loads(raw)
            tipo, d = ev.get("tipo"), ev.get("datos", {})
            typer.echo(f"\n== {tipo} ==")
            if tipo == "plan_generado":
                for p in d.get("plan", {}).get("pasos", []):
                    typer.echo(f"  {p['numero']}. [{p['herramienta']}] {p['titulo']}")
            elif tipo == "archivo_modificado":
                typer.echo(d.get("diff", "")[:3000])
            elif tipo == "archivo_restaurado":
                typer.echo(f"deshecho {d.get('path')}\n{d.get('diff', '')[:3000]}")
            elif tipo == "comando_ejecutado":
                typer.echo(f"$ {d.get('comando')}\n{d.get('salida', '')[:3000]}")
            elif tipo == "instruccion_usuario":
                adj = ", ".join(a.get("path", "?") for a in d.get("adjuntos", []))
                typer.echo(f"(tú) {d.get('texto', '')}" + (f"  [adjuntos: {adj}]" if adj else ""))
            elif tipo == "tarea_pausada":
                typer.echo("pausada — /resume para continuar")
            elif tipo == "tarea_reanudada":
                typer.echo("reanudada")
            elif tipo == "estado_actual":
                typer.echo(f"estado={d.get('estado')} pasos={d.get('pasos_completados')}/{d.get('total_pasos')} "
                           f"pausado={d.get('pausado')}")
            elif tipo == "lista_archivos":
                typer.echo("\n".join(d.get("archivos", [])[:50]))
            elif tipo == "ayuda":
                for c in d.get("comandos", []):
                    typer.echo(f"  {c['cmd']} — {c['desc']}")
            elif tipo == "tarea_finalizada":
                typer.echo(d.get("resumen", ""))
                break
            else:
                typer.echo(json.dumps(d, ensure_ascii=False)[:1000])


@app.command()
def historial():
    r = httpx.get(f"{API}/tareas", headers=_h())
    r.raise_for_status()
    for t in r.json():
        typer.echo(f"#{t['id']} [{t['estado']}] ({t['modelo']}) {t['objetivo']}")


if __name__ == "__main__":
    app()
