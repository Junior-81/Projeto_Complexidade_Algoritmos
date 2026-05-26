import { useMemo, useState, useEffect } from "react";
import { MapContainer, Polyline, Popup, TileLayer } from "react-leaflet";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const OPTIONS_TIMEOUT_MS = 8000;

const MODAL_COLORS = {
  walk: "#2e7d32",
  bike: "#0288d1",
  car: "#546e7a",
  moto: "#ef6c00",
  bus: "#d32f2f",
  uber: "#212121",
  uber_car: "#212121",
  uber_moto: "#6d4c41",
};

const MODAL_LABELS = {
  walk: "A pé",
  bike: "Bike",
  car: "Carro",
  moto: "Moto",
  bus: "Ônibus",
  uber: "Uber",
  uber_car: "Uber Carro",
  uber_moto: "Uber Moto",
};

const ROUTE_MODE_OPTIONS = [
  { value: "auto", label: "Automático" },
  { value: "walk", label: "A pé" },
  { value: "bike", label: "Bike" },
  { value: "car", label: "Carro" },
  { value: "moto", label: "Moto" },
  { value: "bus", label: "Ônibus" },
  { value: "uber_car", label: "Uber Carro" },
  { value: "uber_moto", label: "Uber Moto" },
];

const ROUTE_RESTRICTION_OPTIONS = [
  { value: "none", label: "Livre" },
  { value: "walk", label: "Somente a pé" },
  { value: "bike", label: "Somente bike" },
  { value: "car", label: "Somente carro" },
  { value: "moto", label: "Somente moto" },
  { value: "bus", label: "Ônibus com acesso a pé" },
  { value: "uber_car", label: "Somente Uber Carro" },
  { value: "uber_moto", label: "Somente Uber Moto" },
];

const SEGMENT_DISPLAY_ORDER = [
  "origem",
  "destino",
  "distancia",
  "tempo",
  "custo",
  "esforco",
  "risco_medio",
  "velocidade_media_kmh",
  "quantidade_arestas",
  "linha",
  "gtfs_shape_id",
  "validacao_gtfs",
  "servico",
];

function getCenter(edges) {
  if (!edges || edges.length === 0) {
    return [-8.062742, -34.8739];
  }
  return edges[0]?.origem || [-8.062742, -34.8739];
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatDuration(hoursValue) {
  const totalMinutes = Math.max(0, Math.round(Number(hoursValue || 0) * 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) {
    return `${minutes} min`;
  }

  if (minutes === 0) {
    return `${hours} h`;
  }

  return `${hours} h ${minutes} min`;
}

async function fetchJson(url, init = {}, timeoutMs = 0) {
  if (!timeoutMs) {
    return fetch(url, init);
  }

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timer);
  }
}

function normalizeValue(value, min, max) {
  const range = max - min;
  if (range === 0) {
    return 0.5;
  }
  return Math.max(0, Math.min(1, (value - min) / range));
}

function toLabel(key) {
  return key
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatFieldValue(key, value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (Array.isArray(value)) {
    return value.join(", ");
  }

  if (typeof value === "boolean") {
    return value ? "Sim" : "Nao";
  }

  if (typeof value === "number") {
    if (key.includes("custo")) {
      return formatMoney(value);
    }

    if (key.includes("esforco")) {
      return `${value} pts`;
    }

    if (key.includes("distancia")) {
      return `${value} km`;
    }

    if (key.includes("tempo")) {
      return formatDuration(value);
    }

    if (key.includes("velocidade")) {
      return `${value} km/h`;
    }

    return `${value}`;
  }

  return String(value);
}

function orderedSegmentEntries(segment) {
  const preferredEntries = SEGMENT_DISPLAY_ORDER
    .filter((key) => key in segment)
    .map((key) => [key, segment[key]]);

  const remainingEntries = Object.entries(segment).filter(
    ([key]) => !SEGMENT_DISPLAY_ORDER.includes(key) && key !== "modo" && key !== "meio"
  );

  return [...preferredEntries, ...remainingEntries];
}

function wrapSingleRoute(routeData) {
  return {
    best_option_id: "single_route",
    options: [
      {
        id: "single_route",
        label: "Rota atual",
        modo_inicial: "walk",
        restricao_modal: null,
        status: "ok",
        rank: 1,
        score: 0,
        resumo: routeData?.resumo || {},
        segments_count: Array.isArray(routeData?.segments)
          ? routeData.segments.length
          : 0,
        edges_count: Array.isArray(routeData?.edges) ? routeData.edges.length : 0,
        route: routeData || {},
      },
    ],
  };
}

function App() {
  const [optionsPayload, setOptionsPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [selectedOptionId, setSelectedOptionId] = useState(null);
  const [routeModeChoice, setRouteModeChoice] = useState("auto");
  const [routeRestriction, setRouteRestriction] = useState("none");

  async function fetchOptionsPayload({ timeoutMs = 0 } = {}) {
    const response = await fetchJson(
      `${API_BASE}/api/options`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      },
      timeoutMs
    );

    if (!response.ok) {
      throw new Error(`Erro ao buscar opcoes (${response.status})`);
    }

    return response.json();
  }

  async function fetchRouteData() {
    const response = await fetchJson(`${API_BASE}/api/route`);

    if (!response.ok) {
      throw new Error(`Erro ao buscar rota (${response.status})`);
    }

    return response.json();
  }

  async function fetchRouteOptions() {
    setError("");
    setLoading(true);
    try {
      const routeData = await fetchRouteData();
      setOptionsPayload(wrapSingleRoute(routeData));
      setLoading(false);

      fetchOptionsPayload({ timeoutMs: OPTIONS_TIMEOUT_MS })
        .then((optionsData) => {
          setOptionsPayload(optionsData);
        })
        .catch(() => {
          // Mantem a rota carregada mesmo se o ranking nao responder a tempo.
        });

      return;
    } catch (routeErr) {
      try {
        const optionsData = await fetchOptionsPayload({ timeoutMs: OPTIONS_TIMEOUT_MS });
        setOptionsPayload(optionsData);
      } catch (optionsErr) {
        setError(routeErr?.message || optionsErr?.message || "Falha ao carregar rota");
      } finally {
        setLoading(false);
      }
    }
  }

  async function recalculate() {
    setError("");
    setRunning(true);
    try {
      const isOfficialNoRestrictionMode =
        routeModeChoice === "auto" && routeRestriction === "none";

      if (isOfficialNoRestrictionMode) {
        try {
          const optionsData = await fetchOptionsPayload();
          setOptionsPayload(optionsData);
          setSelectedOptionId(optionsData?.best_option_id || null);
        } catch {
          const fallbackResponse = await fetch(`${API_BASE}/api/calculate`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ modo_inicial: null, restricao_modal: null }),
          });

          if (!fallbackResponse.ok) {
            throw new Error(`Erro ao recalcular rota (${fallbackResponse.status})`);
          }

          const routeData = await fallbackResponse.json();
          setOptionsPayload(wrapSingleRoute(routeData));
          setError("Nao foi possivel carregar ranking de opcoes; exibindo rota sem restricao.");
        }
        return;
      }

      const resolvedMode =
        routeModeChoice === "auto" && routeRestriction !== "none"
          ? routeRestriction
          : routeModeChoice;

      const payload = {
        modo_inicial: resolvedMode === "auto" ? null : resolvedMode,
        restricao_modal: routeRestriction === "none" ? null : routeRestriction,
      };

      const response = await fetch(`${API_BASE}/api/calculate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const detail = payload?.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : detail?.message || `Erro ao recalcular rota (${response.status})`
        );
      }

      const routeData = await response.json();
      setOptionsPayload(wrapSingleRoute(routeData));
    } catch (err) {
      setError(err.message || "Falha no recalculo");
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    fetchRouteOptions();
  }, []);

  const options = optionsPayload?.options || [];

  useEffect(() => {
    if (options.length === 0) {
      return;
    }

    const hasSelected = options.some((option) => option.id === selectedOptionId);
    if (hasSelected) {
      return;
    }

    const bestId = optionsPayload?.best_option_id;
    if (bestId && options.some((option) => option.id === bestId)) {
      setSelectedOptionId(bestId);
      return;
    }

    const firstValid = options.find((option) => option.status === "ok");
    setSelectedOptionId(firstValid?.id || options[0]?.id || null);
  }, [options, optionsPayload, selectedOptionId]);

  const selectedOption = useMemo(
    () => options.find((option) => option.id === selectedOptionId) || null,
    [options, selectedOptionId]
  );

  const routeData = selectedOption?.route || null;
  const edges = routeData?.edges || [];
  const segments = routeData?.segments || [];
  const summary = routeData?.resumo || {};

  const failedOptions = useMemo(
    () => options.filter((option) => option.status === "error"),
    [options]
  );

  const firstErrorMessage = useMemo(() => {
    if (failedOptions.length === 0) {
      return "";
    }
    const first = failedOptions[0];
    return (
      first?.error?.message ||
      first?.error?.stderr ||
      "Falha ao calcular as opcoes de rota."
    );
  }, [failedOptions]);

  const center = useMemo(() => {
    if (edges.length > 0) {
      return getCenter(edges);
    }
    return getCenter(edges);
  }, [edges]);

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Route Web</p>
          <h1>Planejador de rotas</h1>
          <p className="hero-subtitle">
            Defina o tipo de locomoção inicial, aplique a regra desejada e acompanhe o trajeto no mapa.
          </p>
        </div>
        <div className="hero-actions">
          <button onClick={fetchRouteOptions} disabled={loading || running}>
            Atualizar dados
          </button>
          <button className="primary" onClick={recalculate} disabled={running}>
            {running ? "Calculando..." : "Recalcular rota"}
          </button>
        </div>
      </header>

      <section className="control-panel">
        <div className="control-card">
          <div className="control-group">
            <label htmlFor="route-mode">Tipo de locomoção inicial</label>
            <select
              id="route-mode"
              value={routeModeChoice}
              onChange={(event) => setRouteModeChoice(event.target.value)}
              disabled={running}
            >
              {ROUTE_MODE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="route-restriction">Regra da rota</label>
            <select
              id="route-restriction"
              value={routeRestriction}
              onChange={(event) => setRouteRestriction(event.target.value)}
              disabled={running}
            >
              {ROUTE_RESTRICTION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <p className="control-help">
            Ajuste a locomoção inicial e a regra de uso para recalcular a rota com o perfil desejado.
          </p>
        </div>
      </section>

      {error ? <div className="error-box">{error}</div> : null}
      {!loading && !error && options.length === 0 && failedOptions.length > 0 ? (
        <div className="error-box">
          Nenhuma opção de rota foi gerada no backend. Motivo: {firstErrorMessage}
        </div>
      ) : null}

      <main className="layout">
        <section className="map-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Mapa</p>
              <h2>Trajeto exibido</h2>
            </div>
            <span className="panel-badge">{segments.length} trechos</span>
          </div>

          {loading ? (
            <div className="loading-state">Carregando rota...</div>
          ) : (
            <MapContainer center={center} zoom={13} className="map-area">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {edges.map((edge, index) => (
                <Polyline
                  key={`${edge.modo}-${index}`}
                  positions={[edge.origem, edge.destino]}
                  pathOptions={{
                    color: MODAL_COLORS[edge.modo] || "#111111",
                    weight: 5,
                    opacity: 0.9,
                  }}
                >
                  <Popup>
                    <strong>{edge.meio || edge.modo}</strong>
                    <br />
                    Distancia: {edge.distancia} km
                    <br />
                    Tempo: {formatDuration(edge.tempo)}
                    <br />
                    Custo: {formatMoney(edge.custo)}
                    <br />
                    Esforco: {Number(edge.esforco || 0).toFixed(3)} pts
                    <br />
                    Risco: {edge.risco}
                  </Popup>
                </Polyline>
              ))}
            </MapContainer>
          )}
        </section>

        <aside className="info-panel">
          <section className="summary-card">
            <div className="summary-grid">
              <article>
                <p>Tempo total</p>
                <h2>{formatDuration(summary.tempo_total)}</h2>
              </article>
              <article>
                <p>Custo total</p>
                <h2>{formatMoney(summary.custo_total)}</h2>
              </article>
              <article>
                <p>Distância</p>
                <h2>{summary.distancia_total || 0} km</h2>
              </article>
            </div>
          </section>


          <section className="segments-list">
            <div className="panel-header panel-header-tight">
              <div>
                <p className="panel-kicker">Detalhes</p>
                <h3>Trechos da rota ({segments.length})</h3>
              </div>
            </div>
            {segments.length === 0 ? (
              <p>Nenhum trecho encontrado.</p>
            ) : (
              segments.map((segment, index) => (
                <article key={`${segment.modo}-${index}`} className="segment-card">
                  <header>
                    <strong>
                      {index + 1}. {segment.meio || segment.modo}
                    </strong>
                    <span
                      className="chip"
                      style={{
                        backgroundColor: MODAL_COLORS[segment.modo] || "#111111",
                      }}
                    >
                      {segment.modo}
                    </span>
                  </header>

                  <p className="segment-quick-view">
                    {segment.distancia} km · {formatDuration(segment.tempo)} · {formatMoney(segment.custo)} · {Number(segment.esforco || 0).toFixed(3)} pts
                  </p>

                  <div className="segment-details-grid">
                    {orderedSegmentEntries(segment).map(([key, value]) => (
                      <div key={`${key}-${index}`} className="detail-row">
                        <span className="detail-label">{toLabel(key)}</span>
                        <span className="detail-value">{formatFieldValue(key, value)}</span>
                      </div>
                    ))}
                  </div>
                </article>
              ))
            )}
          </section>
        </aside>
      </main>
    </div>
  );
}

export default App;
