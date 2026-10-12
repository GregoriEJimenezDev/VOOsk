import React, { useEffect, useState } from 'react';
import Editor, { loader } from '@monaco-editor/react';

export function langDe(path) {
  const ext = (String(path).split('.').pop() || '').toLowerCase();
  return {
    js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript',
    json: 'json', html: 'html', css: 'css', py: 'python', md: 'markdown',
    yml: 'yaml', yaml: 'yaml', xml: 'xml', sql: 'sql', sh: 'shell',
  }[ext] || 'plaintext';
}

// Editor de código (Monaco, el de VS Code) con respaldo a textarea
// si el CDN no carga (modo simple, misma función).
export function CodeEditor({ path, value, onChange, readOnly }) {
  const [estado, setEstado] = useState('cargando'); // cargando | monaco | simple

  useEffect(() => {
    let vivo = true;
    const t = setTimeout(() => vivo && setEstado((e) => (e === 'cargando' ? 'simple' : e)), 12000);
    loader.init()
      .then(() => { if (vivo) { clearTimeout(t); setEstado('monaco'); } })
      .catch(() => { if (vivo) { clearTimeout(t); setEstado('simple'); } });
    return () => { vivo = false; clearTimeout(t); };
  }, []);

  if (estado === 'cargando') return <div className="code-loading">Cargando editor…</div>;
  if (estado === 'simple' || !Editor) {
    return (
      <textarea
        className="code-simple"
        value={value}
        readOnly={readOnly}
        spellCheck={false}
        onChange={(e) => onChange && onChange(e.target.value)}
      />
    );
  }
  return (
    <Editor
      height="100%"
      theme="vs-dark"
      language={langDe(path)}
      path={path}
      value={value}
      onChange={(v) => onChange && onChange(v ?? '')}
      options={{
        readOnly: !!readOnly,
        minimap: { enabled: false },
        fontSize: 13,
        automaticLayout: true,
        scrollBeyondLastLine: false,
        wordWrap: 'on',
      }}
    />
  );
}
