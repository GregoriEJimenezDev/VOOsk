import React from 'react';
import './styles.css';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login, Dashboard } from './pages/Dashboard.jsx';
import { TaskDetail } from './pages/TaskDetail.jsx';
import { AuthCallback } from './pages/AuthCallback.jsx';
import { Ayuda } from './pages/Ayuda.jsx';
import { Tareas } from './pages/Tareas.jsx';
import { EditorPag } from './pages/Editor.jsx';

function Req({ children }) {
  if (!localStorage.getItem('token')) return <Navigate to="/login" />;
  return children;
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/ayuda" element={<Ayuda />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/" element={<Req><Dashboard /></Req>} />
      <Route path="/tareas" element={<Req><Tareas /></Req>} />
      <Route path="/editor" element={<Req><EditorPag /></Req>} />
      <Route path="/editor/:tid" element={<Req><EditorPag /></Req>} />
      <Route path="/tarea/:id" element={<Req><TaskDetail /></Req>} />
    </Routes>
  </BrowserRouter>
);
