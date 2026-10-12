"""Herramientas del agente: filesystem + shell, con sandbox y aprobación."""
from __future__ import annotations
import difflib
import os
import re
import subprocess
from pathlib import Path
from app.config import settings

COMANDOS_PELIGROSOS = ("rm -rf", "rm -rf /", "rm -rf ~", "del /f", "del /s", "rd /s",
                       "rmdir /s", "format", "mkfs", ":(){:|:&};:",
                       "shutdown", "reboot", "reg delete", "diskpart", "bcdedit",
                       "takeown", "cipher /w",
                       "-encodedcommand", "-enc ", "invoke-expression", "iex(",
                       "| sh", "| bash", "| powershell", "| cmd")
COMANDOS_SOLO_LECTURA = ("dir", "ls", "cat", "type", "echo", "python --version",
                         "node --version", "git status", "pytest --collect-only")

# Carpetas del sistema donde NUNCA se permite trabajar (anti ransomware/destrozos)
RAICES_PROHIBIDAS = ("c:\\windows", "c:\\program files", "c:\\program files (x86)",
                     "/etc", "/bin", "/sbin", "/usr/bin", "/usr/sbin", "/system", "/windows")


class Herramientas:
    def __init__(self, workspace: str | None = None):
        self.root = Path(workspace or settings.WORKSPACE).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.historial: dict[str, list[str]] = {}  # path -> contenidos previos (para /undo)
        self._orden: list[str] = []                # paths por recencia de escritura

    def _ruta_segura(self, path: str) -> Path:
        p = (self.root / path.strip().lstrip("/\\")).resolve()
        if self.root not in p.parents and p != self.root:
            raise PermissionError(f"Ruta fuera del workspace: {path}")
        return p

    @staticmethod
    def validar_raiz(ruta: str) -> str:
        """Normaliza la carpeta de trabajo y rechaza carpetas del sistema."""
        r = str(Path(ruta).expanduser().resolve())
        bajo = r.lower().replace("/", "\\")
        for p in RAICES_PROHIBIDAS:
            pp = p.replace("/", "\\")
            if bajo == pp or bajo.startswith(pp + "\\"):
                raise ValueError(f"Carpeta del sistema no permitida: {ruta}")
        return r

    @staticmethod
    def extraer_path(texto: str) -> str:
        m = re.search(r"[\"']([\w\-./\\ ]+\.\w{1,10})[\"']", texto or "")
        if m:
            return m.group(1).strip()
        m = re.search(r"([\w\-./\\]+\.\w{1,10})", texto or "")
        if m:
            return m.group(0)
        for conocido in ("Dockerfile", "Makefile", "README", "LICENSE", "CHANGELOG"):
            if conocido.lower() in (texto or "").lower():
                return conocido
        toks = re.findall(r"[\w\-./\\]+", texto or "")
        return toks[-1] if toks else "notas.txt"

    @staticmethod
    def extraer_comando(texto: str) -> str:
        m = re.search(r"`([^`]+)`", texto)
        if m:
            return m.group(1).strip()
        bajo = texto.lower()
        if "listar" in bajo or "dir" in bajo or "archivos" in bajo:
            return "dir" if os.name == "nt" else "ls -la"
        return "echo hola-mvp"

    def leer_archivo(self, path: str) -> str:
        p = self._ruta_segura(path)
        if p.suffix.lower() in (".pdf", ".docx"):
            texto, _ = self.leer_documento(path)
            return texto or f"(documento {path} sin texto extraíble)"
        if not p.exists():
            return f"(archivo {path} no existe aún en el workspace)"
        return p.read_text(encoding="utf-8", errors="replace")

    DOCS_TEXTO = frozenset({".txt", ".md", ".markdown", ".csv", ".json", ".js",
                            ".jsx", ".ts", ".tsx", ".html", ".css", ".py", ".log",
                            ".xml", ".yml", ".yaml", ".toml", ".ini", ".sql"})

    def leer_documento(self, path: str, limite: int = 12000) -> tuple[str, str]:
        """Extrae texto de PDF/DOCX/texto. Devuelve (texto, tipo)."""
        p = self._ruta_segura(path)
        if not p.exists():
            return f"(documento {path} no existe aún)", "ausente"
        ext = p.suffix.lower()
        if ext == ".pdf":
            from pypdf import PdfReader
            texto = "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
            return texto.strip()[:limite], "pdf"
        if ext == ".docx":
            import docx
            texto = "\n".join(par.text for par in docx.Document(str(p)).paragraphs)
            return texto.strip()[:limite], "docx"
        if ext in self.DOCS_TEXTO or not ext:
            return p.read_text(encoding="utf-8", errors="replace")[:limite], "texto"
        return (f"(binario {ext}, {p.stat().st_size} bytes — no legible como texto)"), "binario"

    EXTENSIONES_PERMITIDAS = frozenset({".pdf", ".docx", ".txt", ".md", ".csv", ".json",
                                        ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
                                        ".py", ".png", ".jpg", ".jpeg"})

    def guardar_bytes(self, nombre: str, data: bytes, limite_mb: int = 10) -> str:
        """Guarda un archivo subido en el workspace (sanitiza el nombre)."""
        if len(data) > limite_mb * 1024 * 1024:
            raise ValueError(f"Archivo muy grande (máx {limite_mb} MB)")
        limpio = Path(nombre).name.strip() or "archivo"
        if Path(limpio).suffix.lower() not in self.EXTENSIONES_PERMITIDAS:
            raise ValueError(f"Extensión no permitida: {limpio}")
        p = self._ruta_segura(limpio)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return limpio

    def _push_version(self, path: str, contenido_previo: str):
        """Guarda versión para /undo (acota a 20 por archivo)."""
        pila = self.historial.setdefault(path, [])
        pila.append(contenido_previo)
        del pila[:-20]
        if path in self._orden:
            self._orden.remove(path)
        self._orden.append(path)

    def modificar_archivo(self, path: str, nuevo_contenido: str) -> str:
        p = self._ruta_segura(path)
        viejo = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        self._push_version(path, viejo)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(nuevo_contenido, encoding="utf-8")
        return "".join(difflib.unified_diff(viejo.splitlines(True), nuevo_contenido.splitlines(True),
                                            fromfile=f"a/{path}", tofile=f"b/{path}"))

    def editar_fragmento(self, path: str, buscar: str, reemplazo: str, todas: bool = False) -> str:
        """Edición quirúrgica: reemplaza un fragmento exacto (ideal para archivos grandes
        donde reescribir todo es frágil). Cualquier extensión de texto vale."""
        p = self._ruta_segura(path)
        if not p.exists():
            raise FileNotFoundError(f"No existe {path} para editar (pide crearlo primero)")
        viejo = p.read_text(encoding="utf-8", errors="replace")
        if not buscar or buscar not in viejo:
            raise ValueError(f"Texto a reemplazar no encontrado en {path}")
        self._push_version(path, viejo)
        nuevo = viejo.replace(buscar, reemplazo) if todas else viejo.replace(buscar, reemplazo, 1)
        p.write_text(nuevo, encoding="utf-8")
        return "".join(difflib.unified_diff(viejo.splitlines(True), nuevo.splitlines(True),
                                            fromfile=f"a/{path}", tofile=f"b/{path}"))

    def deshacer(self, path: str | None = None, n: int = 1) -> list[tuple[str, str]]:
        """Restaura contenidos previos. Devuelve [(path, diff_actual→restaurado)]."""
        objetivos = [path] if path else list(reversed(self._orden))
        res: list[tuple[str, str]] = []
        for p in objetivos:
            pila = self.historial.get(p, [])
            for _ in range(n):
                if not pila:
                    break
                anterior = pila.pop()
                rp = self._ruta_segura(p)
                actual = rp.read_text(encoding="utf-8", errors="replace") if rp.exists() else ""
                rp.parent.mkdir(parents=True, exist_ok=True)
                rp.write_text(anterior, encoding="utf-8")
                diff = "".join(difflib.unified_diff(
                    actual.splitlines(True), anterior.splitlines(True),
                    fromfile=f"a/{p}", tofile=f"b/{p} (restaurado)"))
                res.append((p, diff))
        if not res:
            raise LookupError("No hay cambios que deshacer" + (f" en {path}" if path else ""))
        return res

    def listar(self, prefijo: str = "", limite: int = 100) -> list[str]:
        base = self._ruta_segura(prefijo) if prefijo else self.root
        if not base.exists():
            return []
        sal: list[str] = []
        for f in sorted(base.rglob("*")):
            if len(sal) >= limite:
                break
            rel = f.relative_to(self.root).as_posix()
            if any(s.startswith(".") for s in rel.split("/")[:1]):
                continue
            if "/." in f"/{rel}":
                continue
            sal.append(rel + ("/" if f.is_dir() else ""))
        return sal

    def ejecutar_comando(self, comando: str, timeout: int = 30) -> str:
        cmd = comando.strip()
        if any(p in cmd for p in COMANDOS_PELIGROSOS):
            raise PermissionError(
                f"El comando '{cmd}' es potencialmente destructivo y requiere aprobación humana.")
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=timeout, cwd=str(self.root))
        salida = (proc.stdout or "") + (proc.stderr or "")
        return salida.strip()[:8000] or f"(sin salida, código {proc.returncode})"
