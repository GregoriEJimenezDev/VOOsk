import { Link } from 'react-router-dom';

// Navegación común de la barra lateral.
export function SideNav({ activa }) {
  const cls = (n) => `sesion${activa === n ? ' activa' : ''}`;
  return (
    <>
      <Link className={cls('inicio')} to="/">🏠 Inicio</Link>
      <Link className={cls('tareas')} to="/tareas">📋 Tareas</Link>
      <Link className={cls('editor')} to="/editor">📁 Editor</Link>
      <Link className={cls('ayuda')} to="/ayuda">❓ Ayuda</Link>
    </>
  );
}
