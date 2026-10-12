import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api.js';
import { SideNav } from '../components/SideNav.jsx';

const FILTROS = [
  ['todas', 'Todas'],
  ['en_curso', 'En curso'],
  ['pendiente', 'Pendientes'],
  ['completada', 'Completadas'],
  ['fallida', 'Fallidas'],
  ['cancelada', 'Canceladas'],
];

function dot(estado) {
  if (estado === 'en_curso') return 'dot-curso';
  if (estado === 'fallida' || estado === 'cancelada') return 'dot-fallo';
  return 'dot-fin';
}

function fecha(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return '';
  }
}

// Apartado de Tareas: historial completo con filtros por estado y borrado.
export function Tareas() {
  const [tareas, setTareas] = useState([]);
  const [filtro, setFiltro] = useState('todas');

  const cargar = async () => {
    try {
      setTareas(await api.historial());
    } catch { /* backend caído */ }
  };
  React.useEffect(() => { cargar(); }, []);

  const borrar = async (id) => {
    if (!window.confirm(`¿Borrar la tarea #${id} y todo su historial?`)) return;
    try {
      await api.borrarTarea(id);
      await cargar();
    } catch (e) {
      alert(String(e.message || e));
    }
  };

  const vis = tareas.filter((t) => filtro === 'todas' || t.estado === filtro);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <h1><img src="/logo.svg" alt="VOOsk" className="logo" />VOOsk</h1>
          <small>agentes · en vivo · sin caja negra</small>
        </div>
        <div className="side-scroll">
          <div className="side-label">Navegar</div>
          <SideNav activa="tareas" />
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <strong>📋 Tareas</strong>
          <span className="pill">{vis.length} de {tareas.length}</span>
        </div>
        <div className="tareas-wrap">
          <div className="filtros">
            {FILTROS.map(([v, label]) => (
              <button key={v} className={`chip-f${filtro === v ? ' activo' : ''}`}
                      onClick={() => setFiltro(v)}>
                {label}
              </button>
            ))}
          </div>
          {vis.length === 0 && <p style={{ color: '#8b93a7' }}>No hay tareas en este filtro.</p>}
          {vis.map((t) => (
            <div key={t.id} className="tarea-card">
              <div className="tarea-head">
                <Link to={`/tarea/${t.id}`}>
                  <span className={`estado-dot ${dot(t.estado)}`} />
                  <strong>#{t.id}</strong> {t.objetivo}
                </Link>
                <button className="btn danger sm" onClick={() => borrar(t.id)} title="Borrar tarea">
                  🗑
                </button>
              </div>
              <div className="tarea-meta">
                <span className="badge">{t.estado}</span>
                <span>{t.modelo}</span>
                <span>{fecha(t.creado)}</span>
                {t.project_id != null && <span>proyecto #{t.project_id}</span>}
              </div>
              {t.resumen && <div className="tarea-resumen">{t.resumen.slice(0, 220)}</div>}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
