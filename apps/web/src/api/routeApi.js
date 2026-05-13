import { API_BASE } from "../config/constants";

export async function fetchOptionsPayload() {
  const response = await fetch(`${API_BASE}/api/options`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    throw new Error(`Erro ao buscar opcoes (${response.status})`);
  }

  return response.json();
}

export async function fetchCurrentRoute() {
  const response = await fetch(`${API_BASE}/api/route`);
  if (!response.ok) {
    throw new Error(`Erro ao buscar rota (${response.status})`);
  }
  return response.json();
}

export async function postCalculate(payload) {
  const response = await fetch(`${API_BASE}/api/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const detail = errorBody?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message || `Erro ao recalcular rota (${response.status})`;
    throw new Error(message);
  }

  return response.json();
}
