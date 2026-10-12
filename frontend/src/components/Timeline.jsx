import React from 'react';

// Línea de tiempo en TIEMPO REAL con estilo terminal oscuro.
const META = {
  tarea_creada: ['Tarea creada', ''],
  plan_generado: ['Plan generado', 'plan'],
  paso_iniciado: ['Paso iniciado', 'paso'],
  herramienta_usada: ['Herramienta', ''],
  archivo_leido: ['Archivo leído', 'archivo'],
  archivo_modificado: ['Archivo modificado', 'archivo'],
  comando_ejecutado: ['Comando', 'comando'],
  accion_requiere_aprobacion: ['Requiere aprobación', 'alerta'],
  aprobacion_humana: ['Aprobada por humano', 'fin'],
  paso_completado: ['Paso completado', 'paso'],
  tarea_finalizada: ['Tarea finalizada', 'fin'],
  instruccion_usuario: ['Tú (en vivo)', 'alerta'],
  instruccion_aplicada: ['Instrucción aplicada', 'fin'],
  archivo_restaurado: ['Archivo restaurado', 'archivo'],
  tarea_pausada: ['Pausada', 'alerta'],
  tarea_reanudada: ['Reanudada', 'fin'],
  tarea_cancelada: ['Cancelada', 'error'],
  estado_actual: ['Estado', ''],
  lista_archivos: ['Archivos', 'archivo'],
  ayuda: ['Ayuda', ''],
  error: ['Error', 'error'],
  modelo_demo: ['Modo demo', 'alerta'],
};

function Diff({ text }) {
  return (
    <pre>
      {String(text || '').split('\n').map((l, i) => (
        <div key={i} className={l.startsWith('+') ? 'diff-add' : l.startsWith('-') ? 'diff-del' : ''}>{l}</div>
      ))}
    </pre>
  );
}

function Evento({ e, onAprobar }) {
  let [label, cls] = META[e.tipo] || [e.tipo, ''];
  const d = e.datos || {};
  if (e.tipo === 'tarea_finalizada' && d.cancelada) { label = 'Tarea cancelada'; cls = 'error'; }
  const esError = d.error === true;
  return (
    <div className="ev">
      <div className="ev-head">
        <span className={`badge ${esError ? 'error' : cls}`}>{label}</span>
        {d.numero != null && <span style={{ color: '#8b93a7' }}>paso {d.numero}</span>}
      </div>

      {e.tipo === 'plan_generado' && (
        <ol>{(d.plan?.pasos || []).map((p) => (
          <li key={p.numero}><code>[{p.herramienta}]</code> <strong>{p.titulo}</strong> — {p.descripcion}</li>
        ))}</ol>
      )}
      {e.tipo === 'paso_iniciado' && <div><strong>{d.titulo}</strong></div>}
      {e.tipo === 'herramienta_usada' && <div><code className="cmd">🔧 {d.herramienta}</code> <span style={{ color: '#8b93a7' }}>{d.titulo}</span></div>}
      {e.tipo === 'archivo_leido' && (
        <details>
          <summary>{d.documento ? '📄' : '📖'} {d.path}</summary>
          <pre>{d.contenido}</pre>
        </details>
      )}
      {e.tipo === 'archivo_modificado' && (
        <div>📝 {d.path}<Diff text={d.diff} /></div>
      )}
      {e.tipo === 'comando_ejecutado' && (
        <div><code className="cmd">$ {d.comando}</code><pre>{d.salida}</pre></div>
      )}
      {e.tipo === 'accion_requiere_aprobacion' && (
        <div className="alerta-box">
          ⚠️ {d.detalle}
          <div style={{ marginTop: 8 }}>
            <button className="btn amber" onClick={() => onAprobar(d.numero)}>Aprobar paso {d.numero}</button>
          </div>
        </div>
      )}
      {e.tipo === 'instruccion_usuario' && (
        <div><div className="user-msg">💬 {d.texto}</div>
          {(d.adjuntos || []).length > 0 && (
            <div style={{ marginTop: 4, fontSize: 12, color: '#8b93a7' }}>
              📎 {(d.adjuntos || []).map((a) => a.path).join(', ')}
            </div>
          )}
        </div>
      )}
      {e.tipo === 'instruccion_aplicada' && (
        <div>📌 Aplicada desde el paso {d.numero}: {(d.instrucciones || []).join(' | ')}</div>
      )}
      {e.tipo === 'tarea_finalizada' && d.cancelada && (
        <div>⛔ Tarea cancelada por el usuario.</div>
      )}
      {e.tipo === 'tarea_finalizada' && !d.cancelada && (
        <div style={{ whiteSpace: 'pre-wrap' }}>{d.resumen}</div>
      )}
      {e.tipo === 'archivo_restaurado' && (
        <div>↩️ {d.path}<Diff text={d.diff} /></div>
      )}
      {e.tipo === 'tarea_pausada' && <div>⏸ Agente en pausa — escribe <code>/resume</code> para continuar.</div>}
      {e.tipo === 'tarea_reanudada' && <div>▶ Agente reanudado.</div>}
      {e.tipo === 'tarea_cancelada' && <div>⛔ Cancelación solicitada…</div>}
      {e.tipo === 'estado_actual' && (
        <pre>{`estado: ${d.estado}\nmodelo: ${d.modelo}\npasos: ${d.pasos_completados}/${d.total_pasos}\npaso actual: ${d.paso_actual ?? '—'}\neventos: ${d.eventos}\npausado: ${d.pausado ? 'sí' : 'no'}`}</pre>
      )}
      {e.tipo === 'lista_archivos' && (
        <details open>
          <summary>📁 {d.prefijo || 'workspace'} ({(d.archivos || []).length})</summary>
          <pre>{(d.archivos || []).join('\n')}</pre>
        </details>
      )}
      {e.tipo === 'ayuda' && (
        <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
          {(d.comandos || []).map((c) => <li key={c.cmd}><code>{c.cmd}</code> — {c.desc}</li>)}
        </ul>
      )}
      {e.tipo === 'error' && <div style={{ color: '#f87171' }}>❌ {d.msg}</div>}
      {e.tipo === 'modelo_demo' && (
        <div className="alerta-box">
          ⚠️ <strong>{d.mensaje}</strong>
          <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
            {(d.pasos || []).map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        </div>
      )}
      {(e.tipo === 'paso_completado' || e.tipo === 'tarea_creada') && (
        <div style={{ whiteSpace: 'pre-wrap' }}>{d.resumen || d.objetivo || JSON.stringify(d)}</div>
      )}
      {!['plan_generado', 'paso_iniciado', 'herramienta_usada', 'archivo_leido',
         'archivo_modificado', 'comando_ejecutado', 'accion_requiere_aprobacion',
         'paso_completado', 'tarea_finalizada', 'tarea_creada',
         'instruccion_usuario', 'instruccion_aplicada', 'archivo_restaurado',
         'tarea_pausada', 'tarea_reanudada', 'tarea_cancelada',
         'estado_actual', 'lista_archivos', 'ayuda', 'error', 'modelo_demo'].includes(e.tipo) && (
        <pre>{JSON.stringify(d, null, 2)}</pre>
      )}
    </div>
  );
}

export function Timeline({ eventos, onAprobar }) {
  return <>{eventos.map((e, i) => <Evento key={i} e={e} onAprobar={onAprobar} />)}</>;
}
