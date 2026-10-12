# VOOsk — MVP

Agentes de IA para desarrollo que muestran **en tiempo real** lo que hacen
(plan, pasos, archivos leídos/modificados con diff, comandos con salida, aprobaciones),
a diferencia de mostrar solo el resultado final.

## Arquitectura (capas + SOLID)

```
backend/app/
  dominio/          entidades, eventos, puertos (ModelAdapter)
  aplicacion/       orquestador desacoplado (no conoce FastAPI ni WS)
  infraestructura/  db (SQLAlchemy+Postgres), seguridad (JWT/Fernet),
                    adapters (groq/ollama gratis + openai/anthropic BYOK),
                    herramientas (sandbox workspace)
  presentacion/     REST + WebSocket
frontend/  React+Vite (REST + WS) — timeline en vivo
cli/       `voosk` (Typer) — MISMA API que el frontend
```

Patrón adapter/strategy: añadir un proveedor = nueva subclase de `ModelAdapter` +
una rama en `construir_adapter()`, sin tocar el orquestador.

## Arranque rápido

```cmd
docker compose up --build
REM backend: http://localhost:8000  frontend: http://localhost:5173
```

Sin Docker (Postgres local):
```cmd
cd backend
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
cd ..\frontend
npm install & npm run dev
pip install -e ..\cli
voosk registro tu@correo-real.com tu-clave
voosk iniciar "Listar archivos del workspace y resumir" --modelo gratuito
```

## Eventos WebSocket (`/ws/tareas/{id}?token=JWT`)

`plan_generado, paso_iniciado, herramienta_usada, archivo_leido, archivo_modificado(diff),
comando_ejecutado(salida), accion_requiere_aprobacion, paso_completado, tarea_finalizada,
instruccion_usuario, instruccion_aplicada`

## Instrucciones en vivo

Con la tarea en curso, escribe en la barra inferior de la vista de tarea
(o envía `{"accion":"instruir","texto":"..."}` por el WebSocket).
La instrucción se muestra al instante en el timeline y el agente la aplica
desde el siguiente paso, sin reiniciar nada.

## Comandos especiales (`/` y `@`)

En la misma barra de la tarea (con autocompletado: `Tab` completa, `Enter` envía):

| Comando | Qué hace |
|---|---|
| `/undo [n] [@archivo]` | revierte las últimas n modificaciones (con diff) |
| `/wait` · `/resume` | pausa y reanuda al agente entre pasos |
| `/stop` | cancela la tarea |
| `/approve [n]` | aprueba un paso pendiente de aprobación |
| `/status` | muestra estado, progreso y si está pausado |
| `/files [prefijo]` | lista archivos del workspace |
| `@archivo` | adjunta el archivo como contexto (ej: `@main.py revísalo`) |
| `/help` | lista los comandos en el timeline |

## Continuar y editar archivos

- **Seguir escribiendo**: `POST /tareas/{id}/continuar {"texto":"..."}` abre una sesión
  nueva que hereda proyecto, modelo, carpeta y el resumen anterior. En la web es
  automático al escribir en una sesión terminada.
- **Archivos**: el agente crea cualquier archivo de texto y edita con dos
  herramientas: `modificar_archivo` (reescritura) y `editar_archivo`
  (reemplazo quirúrgico BUSCAR→REEMPLAZO, ideal para archivos grandes).

## Documentos y vista previa del frontend

- **Adjuntar**: botón 📎 del inicio (PDF, DOCX, TXT, MD, CSV, JSON; máx 10 MB).
  El agente lee el contenido como contexto; en vivo usa `@archivo`.
- **Generar frontend**: pide `index.html` (+ CSS/JS) en la carpeta del proyecto.
- **Verlo**: botón 👁 Vista previa en la tarea (iframe lado a lado) o
  `GET /vista/{tarea_id}/{ruta}` (ej: `/vista/3/index.html?token=JWT`).
  Sirve archivos estáticos del workspace con protección anti path-traversal.

## Login con Google (opcional)

1. Ve a https://console.cloud.google.com/apis/credentials → Crear credenciales
   → ID de cliente OAuth (tipo "Aplicación web").
2. Añade como URI de redirección: `http://localhost:8000/auth/google/callback`
3. Copia Client ID/Secret a `backend/.env`:
   `GOOGLE_CLIENT_ID=…`, `GOOGLE_CLIENT_SECRET=…`, `FRONTEND_URL=http://localhost:5174`
4. Reinicia el backend. En el login verás "Continuar con Google".
   Sin configurar, el botón avisa y puedes seguir con correo+clave (cualquier
   email con formato válido sirve, incluido tu correo real).

Seguridad: credenciales BYOK cifradas con Fernet en reposo; jamás se devuelven por API ni se loguean.
