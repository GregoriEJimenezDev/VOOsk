import React, { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { api } from '../api.js';
import { SideNav } from '../components/SideNav.jsx';

function dot(estado) {
  if (estado === 'en_curso') return 'dot-curso';
  if (estado === 'fallida') return 'dot-fallo';
  return 'dot-fin';
}

function mensajeError(msg, esRegistro) {
  // Garantiza string: el backend a veces devuelve detail como array (422 pydantic).
  try {
    const j = JSON.parse(msg);
    const d = j.detail;
    if (typeof d === 'string') return esRegistro ? d : `${d} — si es tu primera vez, usa Registro.`;
    if (Array.isArray(d)) return d.map((x) => (x && x.msg) || JSON.stringify(x)).join(' | ');
    return msg;
  } catch {
    return msg;
  }
}

export function Login() {
  const [email, setEmail] = useState('demo@example.com');
  const [password, setPassword] = useState('demo1234');
  const [error, setError] = useState('');
  const nav = useNavigate();
  const go = async (fn, esRegistro) => {
    setError('');
    try {
      const r = await fn(email, password);
      localStorage.setItem('token', r.access_token);
      nav('/');
    } catch (e) {
      const msg = String((e && e.message) || '');
      if (/failed to fetch|networkerror|load failed|fetch failed/i.test(msg)) {
        setError('No se pudo conectar. ¿El backend corre en http://localhost:8000?');
        return;
      }
      try {
        const txt = mensajeError(msg, esRegistro);
        setError(typeof txt === 'string' ? txt : 'Error inesperado del servidor');
        return;
      } catch {
        setError('Error inesperado del servidor');
        return;
      }
    }
  };
  return (
    <div className="login-wrap">
      <div className="login-card">
        <h2><img src="/logo.svg" alt="VOOsk" className="logo" />VOOsk</h2>
        <p>Agentes de código que muestran todo lo que hacen, en vivo.</p>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" />
        {error && <p style={{ color: '#f87171' }}>{error}</p>}
        <div className="row">
          <button className="btn full" onClick={() => go(api.login, false)}>Entrar</button>
          <button className="btn ghost full" onClick={() => go(api.registro, true)}>Registro</button>
        </div>
        <div style={{ textAlign: 'center', color: '#8b93a7', fontSize: 12, margin: '12px 0 8px' }}>o</div>
        <button className="google-btn" onClick={async () => {
          setError('');
          try {
            const r = await api.googleUrl();
            window.location.href = r.url;
          } catch {
            setError('Google no configurado en el servidor (ver README: GOOGLE_CLIENT_ID).');
          }
        }}>
          <span style={{ fontWeight: 800 }}>G</span> Continuar con Google
        </button>
        <p style={{ textAlign: 'center', fontSize: 12, marginTop: 12 }}>
          <Link to="/ayuda">❓ ¿Cómo instalar VOOsk? Ver ayuda</Link>
        </p>
      </div>
    </div>
  );
}

export function Dashboard() {
  const [objetivo, setObjetivo] = useState('');
  const [modelo, setModelo] = useState('auto');
  const [historial, setHistorial] = useState([]);
  const [creds, setCreds] = useState([]);
  const [estadoM, setEstadoM] = useState(null);
  const [prov, setProv] = useState('openai');
  const [key, setKey] = useState('');
  const [lanzando, setLanzando] = useState(false);
  const [adjuntos, setAdjuntos] = useState([]);
  const [subiendo, setSubiendo] = useState(false);
  const nav = useNavigate();
  const loc = useLocation();

  const cargar = async () => {
    try {
      setHistorial(await api.historial());
      setCreds(await api.credenciales());
    } catch { /* backend caído: el composer sigue visible */ }
    try {
      setEstadoM(await api.estadoModelos());
    } catch { /* sin estado: se asume demo */ }
  };
  React.useEffect(() => { cargar(); }, [loc.key]);

  const lanzar = async () => {
    if (!objetivo.trim() || lanzando) return;
    setLanzando(true);
    try {
      const t = await api.crearTarea(objetivo, modelo, adjuntos, undefined, '');
      setAdjuntos([]);
      nav(`/tarea/${t.id}`);
    } finally {
      setLanzando(false);
    }
  };
  const subir = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setSubiendo(true);
    try {
      const r = await api.subirArchivo(f);
      setAdjuntos((a) => [...a, r.path]);
    } catch { /* extensión/tamaño inválido: el backend responde el motivo */ }
    finally { setSubiendo(false); e.target.value = ''; }
  };
  const guardarKey = async () => {
    if (!key.trim()) return;
    await api.guardarCredencial(prov, 'byok', key);
    setKey('');
    await cargar();
  };
  const salir = () => { localStorage.removeItem('token'); nav('/login'); };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <h1><img src="/logo.svg" alt="VOOsk" className="logo" />VOOsk</h1>
          <small>agentes · en vivo · sin caja negra</small>
        </div>
        <div className="side-scroll">
          <div className="side-label">Navegar</div>
          <SideNav activa="inicio" />
          <div className="side-label">Sesiones</div>
          {historial.length === 0 && <div style={{ color: '#8b93a7', fontSize: 13 }}>Sin sesiones aún.</div>}
          {historial.map((t) => (
            <Link key={t.id} className="sesion" to={`/tarea/${t.id}`}>
              <span className={`estado-dot ${dot(t.estado)}`} />#{t.id} · {t.objetivo.slice(0, 32)}
            </Link>
          ))}
        </div>
        <div className="side-foot">
          <details>
            <summary>BYOK — claves propias</summary>
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <select value={prov} onChange={(e) => setProv(e.target.value)}>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="groq">Groq</option>
              </select>
              <input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="sk-..." style={{ flex: 1, minWidth: 0 }} />
              <button className="btn ghost" onClick={guardarKey}>OK</button>
            </div>
            <ul style={{ paddingLeft: 18 }}>
              {creds.map((c) => <li key={c.id}>{c.proveedor}{c.tiene_key ? ' · key ✓' : ''}</li>)}
            </ul>
          </details>
          <div style={{ marginTop: 8 }}>
            <Link to="/ayuda" style={{ fontSize: 13 }}>❓ Ayuda y documentación</Link>
          </div>
          <button className="btn ghost full" style={{ marginTop: 8 }} onClick={salir}>Salir</button>
        </div>
      </aside>

      <main className="main">
        <div className="hero">
          <h2>¿Qué construimos <span>hoy</span>?</h2>
          <p>Describe la tarea. Verás el plan, cada paso, cada archivo y cada comando — en tiempo real.</p>
          {estadoM?.demo && (
            <div className="demo-banner">
              ⚠️ <strong>Modo demo:</strong> no hay ningún modelo de IA conectado y las respuestas
              serán plantillas. Para una IA real y gratis: 1) abre la app de <strong>Ollama</strong> en
              tu PC, o 2) crea una key en <strong>console.groq.com</strong> y pégala abajo en BYOK → Groq.
            </div>
          )}
          {estadoM && !estadoM.demo && (
            <div className="ok-banner">
              ✅ IA real activa: <strong>{estadoM.recomendado}</strong>
              {estadoM.ollama?.modelos?.length > 0 && estadoM.recomendado === 'ollama'
                && ` (${estadoM.ollama.modelos[0]})`}
            </div>
          )}
          <div className="composer">
            <textarea
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) lanzar(); }}
              placeholder="Ej: lista los archivos del workspace y resume el proyecto…  (Ctrl+Enter para lanzar)"
            />
            {adjuntos.length > 0 && (
              <div className="chips">
                {adjuntos.map((a) => <span key={a} className="chip">📄 {a}</span>)}
              </div>
            )}
            <div className="composer-bar">
              <label className="btn ghost" title="Adjuntar documento (PDF/DOCX/TXT)" style={{ cursor: 'pointer' }}>
                {subiendo ? '…' : '📎'}
                <input type="file" hidden onChange={subir} accept=".pdf,.docx,.txt,.md,.csv,.json" />
              </label>
              <select value={modelo} onChange={(e) => setModelo(e.target.value)} title="Modelo">
                <option value="auto">✨ auto (recomendado)</option>
                <option value="ollama">ollama local</option>
                <option value="groq">groq</option>
                <option value="openai">openai (BYOK)</option>
                <option value="anthropic">anthropic (BYOK)</option>
              </select>
              <span style={{ flex: 1 }} />
              <button className="btn" onClick={lanzar} disabled={lanzando || !objetivo.trim()}>
                {lanzando ? 'Lanzando…' : '▶ Ejecutar'}
              </button>
            </div>
          </div>

          {historial.length > 0 && (
            <div className="recent">
              <div className="side-label">Recientes</div>
              {historial.slice(0, 5).map((t) => (
                <Link key={t.id} className="sesion" to={`/tarea/${t.id}`}>
                  <span className={`estado-dot ${dot(t.estado)}`} />[{t.estado}] {t.objetivo}
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
