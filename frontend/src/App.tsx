import { useEffect, useState } from "react";
import { fetchHealth } from "./api/client";
import type { HealthResponse } from "./types/health";
export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { fetchHealth().then(setHealth).catch((err) => setError(String(err))); }, []);
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>RADAR LAB</h1><p>Fundacion - Paso 1 + Paso 2</p>
      {error && <p style={{ color: "red" }}>Error: {error}</p>}
      {health && <p style={{ color: "green" }}>Backend: {health.status} (v{health.version})</p>}
      {!health && !error && <p>Cargando estado del backend...</p>}
    </div>
  );
}