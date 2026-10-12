import { useEffect, useRef, useState } from 'react';
import { wsUrl } from '../api.js';

// Hook: consume el MISMO WebSocket de eventos incrementales que el CLI.
export function useTaskSocket(tareaId) {
  const [eventos, setEventos] = useState([]);
  const [estado, setEstado] = useState('conectando');
  const wsRef = useRef(null);

  useEffect(() => {
    if (!tareaId) return;
    const ws = new WebSocket(wsUrl(tareaId));
    wsRef.current = ws;
    ws.onopen = () => setEstado('en_vivo');
    ws.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data);
        setEventos((prev) => [...prev, ev]);
        if (ev.tipo === 'tarea_finalizada') setEstado('finalizada');
      } catch {}
    };
    ws.onclose = () => setEstado((e) => (e === 'finalizada' ? e : 'desconectado'));
    return () => ws.close();
  }, [tareaId]);

  const aprobar = (numero) => wsRef.current?.send(JSON.stringify({ accion: 'aprobar', numero }));
  const instruir = (texto) => wsRef.current?.send(JSON.stringify({ accion: 'instruir', texto }));
  return { eventos, estado, aprobar, instruir };
}
