import React from 'react';
import { Link } from 'react-router-dom';

// Apartado público de Ayuda y documentación: instalar desde terminal,
// comandos, Google OAuth y seguridad.
function Bloque({ titulo, children }) {
  return (
    <section className="ayuda-bloque">
      <h3>{titulo}</h3>
      {children}
    </section>
  );
}

export function Ayuda() {
  return (
    <div className="ayuda-wrap">
      <div className="ayuda-card">
        <Link to="/">← Volver a VOOsk</Link>
        <h2><img src="/logo.svg" alt="VOOsk" className="logo" /> Ayuda y documentación</h2>

        <Bloque titulo="1. Instalar el backend (terminal)">
          <pre>{`cd "C:\\ruta\\a\\IA-inteligengte\\backend"
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
# Genera claves (pégalas en .env):
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Arrancar (SQLite rápido, sin Postgres):
$env:DATABASE_URL = "sqlite:///./dev.db"
python -m uvicorn app.main:app --reload
# → http://127.0.0.1:8000/docs`}</pre>
          <p>Con Postgres: instala PostgreSQL 16, crea la BD <code>ia_transparente</code> y usa <code>DATABASE_URL=postgresql+psycopg://ia:ia@localhost:5432/ia_transparente</code>.</p>
        </Bloque>

        <Bloque titulo="2. Instalar el frontend">
          <pre>{`cd "C:\\ruta\\a\\IA-inteligengte\\frontend"
npm install
npm run dev
# → http://localhost:5173 (o el puerto que indique Vite)`}</pre>
        </Bloque>

        <Bloque titulo="3. Usar VOOsk desde la terminal (CLI)">
          <pre>{`pip install -e "C:\\ruta\\a\\IA-inteligengte\\cli"
# Si 'voosk' no se reconoce, usa: python -m ... o agrega Scripts al PATH.
# En esta sesión el comando vive como módulo; alternativa directa:
voosk registro tu@correo-real.com tu-clave
voosk login tu@correo-real.com tu-clave
voosk iniciar "Crear una API de tareas en mi carpeta" --ruta "C:\\mis-proyectos\\tienda"
voosk ver 3
voosk historial
voosk proyectos
voosk ayuda`}</pre>
          <p>El CLI consume la <strong>misma API</strong> que la web y muestra los eventos en vivo en tu consola.</p>
        </Bloque>

        <Bloque titulo="4. Entrar con Google">
          <p>En el login pulsa <strong>Continuar con Google</strong>. Para activarlo el servidor necesita:</p>
          <pre>{`# 1. https://console.cloud.google.com/apis/credentials
#    Crear ID de cliente OAuth (app web) con redirección a:
#    http://localhost:8000/auth/google/callback
# 2. En backend/.env:
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
FRONTEND_URL=http://localhost:5174
# 3. Reinicia el backend.`}</pre>
        </Bloque>

        <Bloque titulo="5. Comandos rápidos en la tarea">
          <pre>{`/undo [n] [@archivo]   revierte cambios
/wait · /resume        pausa y reanuda
/stop                  cancela la tarea
/approve [n]           aprueba un paso
/status                estado y progreso
/files [prefijo]       lista la carpeta
@archivo               adjunta contexto
/help                  ayuda en el timeline`}</pre>
          <p><strong>Seguir escribiendo:</strong> si la sesión terminó y escribes de nuevo,
          VOOsk abre automáticamente una <em>continuación</em> que hereda proyecto, modelo,
          carpeta y lo ya hecho. Nada se pierde.</p>
          <p><strong>Archivos:</strong> el agente crea cualquier archivo de texto
          (<code>.html</code>, <code>.css</code>, <code>.js</code>, <code>.py</code>,
          <code>.json</code>…) y edita los existentes de forma quirúrgica
          (solo el fragmento que cambia, con diff visible).</p>
        </Bloque>

        <Bloque titulo="6. Documentos y frontend generado">
          <p><strong>Adjuntar documentos:</strong> en el inicio pulsa 📎 y sube PDF, Word o texto
          (máx 10 MB). Quedan como chips en el composer y el agente los lee como contexto.
          En la tarea, menciónalos con <code>@informe.pdf</code> para adjuntarlos en vivo.</p>
          <p><strong>Generar frontend:</strong> pide p. ej. <em>"crea una landing con index.html
          y estilos"</em> en la carpeta del proyecto. Luego pulsa <strong>👁 Vista previa</strong>:
          verás la web renderizada al lado del timeline, actualizándose con cada cambio
          (o ábrela en pestaña con ↗). Sirve cualquier archivo estático: HTML, CSS, JS, imágenes.</p>
        </Bloque>

        <Bloque titulo="7. Editor de código">
          <p>En <strong>📁 Editor</strong> ves todos los archivos creados, con explorador de
          carpetas y editor estilo VS Code (colores por lenguaje, <code>Ctrl+S</code> guarda).
          Puedes <strong>editar el código manualmente</strong>; al guardar entra al historial,
          así que <code>/undo</code> también revierte tus cambios a mano. Desde una tarea,
          entra con <strong>📁 Abrir en editor</strong> para ver su carpeta exacta.</p>
        </Bloque>

        <Bloque titulo="8. Seguridad">
          <ul>
            <li>Claves BYOK <strong>cifradas con Fernet</strong> en reposo; nunca se devuelven por API.</li>
            <li>Los eventos se <strong>redactan</strong>: si un archivo o comando contiene una <code>sk-…</code>, se guarda como <code>[SECRETO]</code>.</li>
            <li>El agente solo toca su <strong>carpeta de trabajo</strong> (sandbox); carpetas del sistema están prohibidas.</li>
            <li>Comandos destructivos (<code>rm -rf</code>, <code>del /s</code>, pipes a shell,…) requieren <strong>aprobación humana</strong>.</li>
            <li>Login con JWT temporal + límite de 30 intentos/min por IP.</li>
            <li>Usa tu correo real o Google; las contraseñas se guardan con hash (PBKDF2).</li>
          </ul>
        </Bloque>
      </div>
    </div>
  );
}
