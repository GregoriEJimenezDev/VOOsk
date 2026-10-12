export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function q(o) {
  return Object.entries(o || {})
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
}

function headers() {
  const t = localStorage.getItem('token');
  return { 'Content-Type': 'application/json', ...(t ? { Authorization: `Bearer ${t}` } : {}) };
}

async function req(path, opts = {}) {
  const t = localStorage.getItem('token');
  const esFD = opts.body instanceof FormData;
  const r = await fetch(API + path, {
    ...opts,
    headers: {
      ...(t ? { Authorization: `Bearer ${t}` } : {}),
      ...(!esFD ? { 'Content-Type': 'application/json' } : {}),
    },
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export const api = {
  registro: (email, password) => req('/auth/registro', { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: (email, password) => req('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  googleUrl: () => req('/auth/google/url'),
  proyectos: () => req('/proyectos'),
  crearProyecto: (nombre, descripcion, ruta) =>
    req('/proyectos', { method: 'POST', body: JSON.stringify({ nombre, descripcion, ruta }) }),
  credenciales: () => req('/credenciales'),
  guardarCredencial: (proveedor, etiqueta, api_key) =>
    req('/credenciales', { method: 'POST', body: JSON.stringify({ proveedor, etiqueta, api_key }) }),
  crearTarea: (objetivo, modelo, archivos, project_id, ruta) =>
    req('/tareas', { method: 'POST', body: JSON.stringify({ objetivo, modelo, archivos, project_id, ruta }) }),
  continuar: (id, texto) =>
    req(`/tareas/${id}/continuar`, { method: 'POST', body: JSON.stringify({ texto }) }),
  historial: () => req('/tareas'),
  detalle: (id) => req(`/tareas/${id}`),
  borrarTarea: (id) => req(`/tareas/${id}`, { method: 'DELETE' }),
  archivos: (prefijo = '', opts = {}) =>
    req(`/archivos?${q({ prefijo, ...opts })}`),
  estadoModelos: () => req('/modelos/estado'),
  leerArchivo: (path, opts = {}) => req(`/archivos/leer?${q({ path, ...opts })}`),
  guardarArchivo: (path, contenido, opts = {}) =>
    req('/archivos/guardar', { method: 'PUT', body: JSON.stringify({ path, contenido, ...opts }) }),
  subirArchivo: (file, ruta = '') => {
    const fd = new FormData();
    fd.append('archivo', file);
    return req(`/archivos/subir?ruta=${encodeURIComponent(ruta)}`, { method: 'POST', body: fd });
  },
};

export function wsUrl(tareaId) {
  const token = localStorage.getItem('token') || '';
  const base = API.replace('http', 'ws');
  return `${base}/ws/tareas/${tareaId}?token=${encodeURIComponent(token)}`;
}

export function vistaUrl(tareaId, ruta = 'index.html') {
  const token = localStorage.getItem('token') || '';
  return `${API}/vista/${tareaId}/${ruta}?token=${encodeURIComponent(token)}`;
}
