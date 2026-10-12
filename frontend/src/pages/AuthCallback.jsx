import React from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';

// Ruta /auth/callback?token=JWT — cierra el flujo de Google OAuth.
export function AuthCallback() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const token = params.get('token');

  React.useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
      nav('/');
    }
  }, [token]);

  if (!token) {
    return (
      <div className="login-wrap">
        <div className="login-card">
          <h2>VOOsk</h2>
          <p>No se recibió token de Google.</p>
          <Link to="/login">Volver al login</Link>
        </div>
      </div>
    );
  }
  return (
    <div className="login-wrap">
      <div className="login-card"><p>Conectando con VOOsk…</p></div>
    </div>
  );
}
