# AGENTS.md — VOOsk

## Qué es
- Agentes de IA con trazabilidad en tiempo real. Monorepo de 3 piezas: `backend/` (FastAPI), `frontend/` (React+Vite), `cli/` (Typer → binario `voosk`). **No hay repositorio git** (sin `.git`, sin `.gitignore`, sin CI).
- **Todo el código, rutas API, eventos WS y mensajes están en español** (nombres de archivos, funciones, claves JSON). Seguir ese naming; no traducir.

## Comandos (Windows, sin Docker)
- Backend: `cd backend && python -m uvicorn app.main:app --reload --port 8000` (Python 3.13; deps: `pip install -r requirements.txt`)
- Frontend: `cd frontend && npm install && npm run dev` → http://localhost:5173. Build: `npm run build` (genera `dist/`, committeado). **No existe script de lint ni de tests.**
- CLI: `pip install -e cli` → `voosk` (alias `ia-transparente`); apunta a `VOOSK_API` (default `http://localhost:8000`).
- Docker: `docker compose up --build` (Postgres :5432, backend :8000, frontend vía nginx :5173). El compose solo inyecta `DATABASE_URL` y `JWT_SECRET`; el resto del `.env` no aplica ahí.
- **No hay tests ni linters en ningún lado.** Verificación mínima de backend sin arrancar servidor:
  `cd backend && python -c "from app.main import app; print(len(app.routes))"` → 25 rutas.
- En Windows los procesos uvicorn lanzados en background mueren al terminar el comando: iniciar servidor y comprobar (`GET http://127.0.0.1:8000/salud`) en **el mismo** comando, con poll/reintentos (~20 s).

## Config / entorno
- `backend/.env` es la única fuente de configuración: la carga `app/config.py` con `python-dotenv` **al importar** (no hace falta `--env-file`). Valores por defecto viven en `Settings`.
- Local usa **SQLite** (`DATABASE_URL=sqlite:///dev.db`); `db/sesion.py` pasa `check_same_thread=False` solo si la URL empieza por `sqlite`.
- **`FRONTEND_URL` debe ser `http://localhost:5173`** (puerto real de Vite; en 5174 el redirect de Google OAuth acaba en 404). CORS en `CORS_ORIGINS`.
- El `.env` contiene `FERNET_KEY`/`JWT_SECRET` y **no está ignorado por git** → nunca subirlo.
- Sin `FERNET_KEY`, `seguridad/crypto.py` genera clave efímera: las claves BYOK guardadas quedan inútiles al reiniciar (aviso en el startup).

## Arquitectura (lo no obvio)
- 4 capas en backend: `dominio/` (entidades + puerto `ModelAdapter`), `aplicacion/` (orquestador/comandos: **no** conoce FastAPI ni WS), `infraestructura/` (db, adapters, seguridad, herramientas), `presentacion/` (REST `rest.py`, WS `ws.py`, `oauth_google.py`).
- **Añadir proveedor de IA** = subclase de `ModelAdapter` + rama en `construir_adapter()` (`infraestructura/adapters/modelos.py`). El orquestador no se toca.
- El campo `modelo` de una tarea guarda `proveedor[:modelo]` (ej. `openai:gpt-4o-mini`); la credencial BYOK se busca por el proveedor (texto antes de `:`).
- BYOK: `POST /credenciales` cifra con Fernet; **jamás** se devuelve por API ni se loguea. `seguridad/redactar.py` redacta claves (`sk-…`, `sk-ant-…`) de todo evento antes de persistirlo en BD y emitirlo por WS.
- Archivos: todo pasa por `Herramientas` (`infraestructura/herramientas/`) con `validar_raiz()` anti path-traversal; no abrir archivos con `open()` directo desde el orquestador. `backend/workspace/` es solo material de demo; la carpeta real por proyecto es `Project.ruta`.
- Web y CLI consumen **la misma** API REST + WS. Eventos y acciones del cliente: ver docstring de `ws.py` y README (fuente canónica del protocolo).
- Login Google: `GET /auth/google/url` → Google → `GET /auth/google/callback` → redirect `FRONTEND_URL/auth/callback?token=JWT`. Sin `GOOGLE_CLIENT_ID/SECRET` responde 501 (el frontend lo muestra como aviso y sigue con email+clave). Pasos de Google Cloud Console en el README.

## Frontend
- Sin proxy: `src/api.js` llama directo a `http://localhost:8000` (override con `VITE_API_URL`).
- JWT en `localStorage.token` (header `Authorization`); va por query `?token=` cuando no se pueden mandar headers (iframe de vista previa y WebSocket).
- Protección de rutas = componente `Req` en `main.jsx` (solo client-side).
