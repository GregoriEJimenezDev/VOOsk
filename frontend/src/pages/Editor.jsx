import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api.js';
import { SideNav } from '../components/SideNav.jsx';
import { CodeEditor } from '../components/CodeEditor.jsx';

// Convierte la lista plana ["a/b.txt", "a/", "c.txt"] en árbol.
function arbol(paths) {
  const root = { dirs: {}, files: [] };
  for (const raw of paths || []) {
    const esDir = raw.endsWith('/');
    const partes = raw.replace(/\/$/, '').split('/');
    let n = root;
    for (let i = 0; i < partes.length; i++) {
      const ultimo = i === partes.length - 1;
      if (ultimo && !esDir) {
        if (!n.files.includes(partes[i])) n.files.push(partes[i]);
      } else {
        n.dirs[partes[i]] = n.dirs[partes[i]] || { dirs: {}, files: [] };
        n = n.dirs[partes[i]];
      }
    }
  }
  return root;
}

function Nodo({ nodo, base, abrir, actual }) {
  const [abierto, setAbierto] = useState(true);
  return (
    <div>
      {Object.keys(nodo.dirs).sort().map((d) => (
        <div key={d}>
          <div className="tree-dir" onClick={() => setAbierto((v) => ({ ...v, [d]: !(v[d] ?? true) }))}>
            {(abierto[d] ?? true) ? '📂' : '📁'} {d}
          </div>
          {(abierto[d] ?? true) && (
            <div style={{ paddingLeft: 14 }}>
              <Nodo nodo={nodo.dirs[d]} base={base + d + '/'} abrir={abrir} actual={actual} />
            </div>
          )}
        </div>
      ))}
      {nodo.files.sort().map((f) => (
        <div key={f} className={`tree-file${actual === base + f ? ' activo' : ''}`}
             onClick={() => abrir(base + f)}>
          📄 {f}
        </div>
      ))}
    </div>
  );
}

// Apartado Editor: explorador de la carpeta + editor de código (Monaco).
// /editor → workspace por defecto · /editor/:tid → carpeta de esa tarea.
export function EditorPag() {
  const { tid } = useParams();
  const [raiz, setRaiz] = useState('');
  const [rutaReal, setRutaReal] = useState('');
  const [lista, setLista] = useState([]);
  const [path, setPath] = useState('');
  const [valor, setValor] = useState('');
  const [original, setOriginal] = useState('');
  const [msg, setMsg] = useState('');

  const opts = () => (tid ? { tarea_id: tid } : raiz.trim() ? { ruta: raiz.trim() } : {});

  const cargar = async (o) => {
    const r = await api.archivos('', o || opts());
    setLista(r.archivos || []);
    setRutaReal(r.ruta || '');
  };
  React.useEffect(() => { cargar().catch((e) => setMsg(String(e.message || e))); }, [tid]); // eslint-disable-line

  const abrir = async (p, forzar) => {
    if (path && valor !== original && !forzar) {
      if (!window.confirm(`¿Descartar cambios sin guardar en ${path}?`)) return;
    }
    try {
      const r = await api.leerArchivo(p, opts());
      setPath(p);
      setValor(r.contenido);
      setOriginal(r.contenido);
      setMsg('');
    } catch (e) {
      setMsg(String(e.message || e));
    }
  };

  const guardar = async () => {
    if (!path) return;
    try {
      const r = await api.guardarArchivo(path, valor, opts());
      setOriginal(valor);
      const n = (r.diff || '').split('\n').filter((l) => l.startsWith('+') || l.startsWith('-')).length;
      setMsg(`✅ Guardado ${path} (${n} líneas en diff — /undo lo revierte)`);
      await cargar();
    } catch (e) {
      setMsg('❌ ' + String(e.message || e));
    }
  };

  const nuevo = () => {
    const n = window.prompt('Nombre del archivo (ej: estilos.css):');
    if (!n) return;
    setPath(n.replace(/^\/+/, ''));
    setValor('');
    setOriginal('@@nuevo@@');
  };

  const sucio = valor !== original;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <h1><img src="/logo.svg" alt="VOOsk" className="logo" />VOOsk</h1>
          <small>editor de código</small>
        </div>
        <div className="side-scroll">
          <div className="side-label">Navegar</div>
          <SideNav activa="" />
          <div className="side-label">Carpeta</div>
          {tid
            ? <div style={{ fontSize: 12, color: '#8b93a7' }}>Tarea #{tid}<br />{rutaReal}</div>
            : (
              <div style={{ display: 'flex', gap: 6 }}>
                <input value={raiz} onChange={(e) => setRaiz(e.target.value)}
                       placeholder="C:\mi-proyecto" style={{ flex: 1, minWidth: 0 }} />
                <button className="btn ghost" onClick={() => cargar().catch((e) => setMsg(String(e.message || e)))}>Ir</button>
              </div>
            )}
          {!tid && rutaReal && <div style={{ fontSize: 12, color: '#8b93a7', marginTop: 6 }}>{rutaReal}</div>}
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          {tid && <Link to={`/tarea/${tid}`}>← tarea #{tid}</Link>}
          <strong>{path || 'Editor'}</strong>
          {sucio && <span className="pill vivo">● sin guardar</span>}
          <span style={{ flex: 1 }} />
          <button className="btn ghost" onClick={nuevo}>＋ Nuevo</button>
          <button className="btn" onClick={guardar} disabled={!path || !sucio}>💾 Guardar</button>
        </div>
        <div className="editor-split">
          <div className="explorer">
            <div className="side-label">Archivos ({lista.length})</div>
            <Nodo nodo={arbol(lista)} base="" abrir={abrir} actual={path} />
          </div>
          <div className="editor-main" onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); guardar(); }
          }}>
            {path
              ? <CodeEditor path={path} value={valor} onChange={setValor} />
              : <div className="editor-vacio">← Elige un archivo o crea uno con ＋ Nuevo<br />(Ctrl+S guarda)</div>}
          </div>
        </div>
        {msg && <div className="editor-msg">{msg}</div>}
      </main>
    </div>
  );
}
