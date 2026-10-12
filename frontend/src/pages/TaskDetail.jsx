import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api, vistaUrl } from '../api.js';
import { SideNav } from '../components/SideNav.jsx';
import { useTaskSocket } from '../hooks/useTaskSocket.js';
import { Timeline } from '../components/Timeline.jsx';

const COMANDOS = [
  { cmd: '/undo', desc: 'revierte últimos cambios (ej: /undo 2 @notas.txt)' },
  { cmd: '/wait', desc: 'pausa al agente' },
  { cmd: '/resume', desc: 'reanuda la tarea' },
  { cmd: '/stop', desc: 'cancela la tarea' },
  { cmd: '/approve', desc: 'aprueba el paso pendiente' },
  { cmd: '/status', desc: 'muestra el estado actual' },
  { cmd: '/files', desc: 'lista archivos del workspace' },
  { cmd: '/help', desc: 'ver ayuda' },
];

export function TaskDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { eventos, estado, aprobar, instruir } = useTaskSocket(id);
  const [texto, setTexto] = useState('');
  const [moviendo, setMoviendo] = useState(false);
  const [sugs, setSugs] = useState([]);
  const [modoSug, setModoSug] = useState(null); // 'cmd' | 'file' | null
  const [verPreview, setVerPreview] = useState(false);
  const finRef = React.useRef(null);

  React.useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [eventos.length]);

  const plan = eventos.find((e) => e.tipo === 'plan_generado')?.datos?.plan;
  const total = plan?.pasos?.length || 0;
  const hechos = eventos.filter((e) => e.tipo === 'paso_completado').length;
  const terminada = estado === 'finalizada';
  const hayFrontend = eventos.some((e) =>
    (e.tipo === 'archivo_modificado' || e.tipo === 'archivo_leido') &&
    /\.html?$/.test(e.datos?.path || ''));

  const onCambiar = async (v) => {
    setTexto(v);
    // Autocompletar /comandos
    if (v.startsWith('/') && !v.includes(' ')) {
      setModoSug('cmd');
      setSugs(COMANDOS.filter((c) => c.cmd.startsWith(v)).slice(0, 8));
      return;
    }
    // Autocompletar @archivos (última mención)
    const m = v.match(/@([\w\-./\\]*)$/);
    if (m) {
      try {
        const r = await api.archivos(m[1]);
        const files = (r.archivos || []).filter((f) => f.toLowerCase().includes(m[1].toLowerCase()));
        setModoSug('file');
        setSugs(files.slice(0, 8).map((f) => ({ cmd: '@' + f, desc: 'adjuntar como contexto' })));
      } catch {
        setSugs([]);
      }
      return;
    }
    setModoSug(null);
    setSugs([]);
  };

  const completar = (s) => {
    if (modoSug === 'cmd') {
      setTexto(s.cmd + ' ');
    } else {
      setTexto(texto.replace(/@[\w\-./\\]*$/, s.cmd + ' '));
    }
    setSugs([]);
    setModoSug(null);
  };

  const enviar = async () => {
    const t = texto.trim();
    if (!t || moviendo) return;
    if (terminada) {
      // Seguir escribiendo en una sesión terminada: bifurca a una nueva
      // que hereda proyecto, modelo, carpeta y contexto. Nada se pierde.
      setMoviendo(true);
      try {
        const nt = await api.continuar(id, t);
        nav(`/tarea/${nt.id}`);
      } catch {
        setMoviendo(false);
      }
      return;
    }
    instruir(t);
    setTexto('');
    setSugs([]);
    setModoSug(null);
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <h1><img src="/logo.svg" alt="VOOsk" className="logo" />VOOsk</h1>
          <small>sesión #{id}</small>
        </div>
        <div className="side-scroll">
          <Link className="btn ghost full" style={{ display: 'block', textAlign: 'center' }} to="/">
            ＋ Nueva tarea
          </Link>
          <Link className="btn ghost full" style={{ display: 'block', textAlign: 'center', marginTop: 6 }} to={`/editor/${id}`}>
            📁 Abrir en editor
          </Link>
          <div className="side-label">Navegar</div>
          <SideNav activa="" />
          <div className="side-label">En esta sesión</div>
          <div style={{ fontSize: 13, color: '#8b93a7' }}>{eventos.length} eventos en vivo</div>
          {total > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 12, color: '#8b93a7' }}>Progreso: {hechos}/{total} pasos</div>
              <div className="progress"><div style={{ width: `${Math.round((hechos / total) * 100)}%` }} /></div>
            </div>
          )}
          <div className="side-label">Vista previa</div>
          <button className="btn ghost full" onClick={() => setVerPreview((v) => !v)}>
            {verPreview ? '👁 Ocultar web' : '👁 Ver frontend'}
          </button>
          <div style={{ marginTop: 8 }}><Link to="/ayuda" style={{ fontSize: 13 }}>❓ Ayuda y docs</Link></div>
          <div className="side-label">Comandos</div>
          <div style={{ fontSize: 12, color: '#8b93a7', lineHeight: 1.7 }}>
            <code>/undo /wait /resume</code><br />
            <code>/stop /approve /status</code><br />
            <code>/files /help @archivo</code>
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <Link to="/">←</Link>
          <strong>Tarea #{id}</strong>
          <span className={`pill ${estado === 'en_vivo' ? 'vivo' : terminada ? 'fin' : ''}`}>
            {estado === 'en_vivo' ? '● en vivo' : estado}
          </span>
          <span style={{ flex: 1 }} />
          <button className="btn ghost" onClick={() => setVerPreview((v) => !v)}>
            {verPreview ? 'Ocultar' : '👁 Vista previa'}
          </button>
          <a href={vistaUrl(id)} target="_blank" rel="noreferrer" style={{ fontSize: 13 }}>↗ pestaña</a>
        </div>
        <div className={verPreview ? 'split' : ''} style={verPreview ? undefined : { display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div className="stream">
            {eventos.length === 0 && (
              <div className="ev"><span className="badge">…</span> Conectando al agente…</div>
            )}
            <Timeline eventos={eventos} onAprobar={aprobar} />
            {!hayFrontend && eventos.length > 2 && (
              <div className="ev"><span className="badge">pista</span> Pide al agente un <code>index.html</code> y míralo aquí con 👁 Vista previa.</div>
            )}
            <div ref={finRef} />
          </div>
          {verPreview && (
            <div className="preview">
              <iframe title="vista previa" src={vistaUrl(id)} />
            </div>
          )}
        </div>
        <div style={{ maxWidth: verPreview ? '100%' : 892, width: '100%', margin: '0 auto' }}>
          {sugs.length > 0 && (
            <div className="sugerencias">
              {sugs.map((s) => (
                <div key={s.cmd} className="sug" onClick={() => completar(s)}>
                  <code>{s.cmd}</code><span>{s.desc}</span>
                </div>
              ))}
            </div>
          )}
          <div className="instruir-bar" style={{ maxWidth: '100%' }}>
            <input
              value={texto}
              onChange={(e) => onCambiar(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') enviar();
                else if (e.key === 'Tab' && sugs.length > 0) { e.preventDefault(); completar(sugs[0]); }
                else if (e.key === 'Escape') { setSugs([]); setModoSug(null); }
              }}
              placeholder={terminada ? 'Sesión terminada — escribe y se abre una continuación' : '/comando, @archivo o instrucción… (Enter envía, Tab autocompleta)'}
            />
            <button className="btn" onClick={enviar} disabled={!texto.trim() || moviendo}>
              {moviendo ? '…' : terminada ? 'Seguir →' : 'Enviar'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
