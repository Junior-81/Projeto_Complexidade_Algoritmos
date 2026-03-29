import { useMemo, useState, useEffect } from "react";
import { MapContainer, Polyline, Popup, TileLayer } from "react-leaflet";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const ALL_MODES_KEY = "all";

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
  walk: "A pe",
  bike: "Bike",
  car: "Carro",
  moto: "Moto",
  bus: "Onibus",
  uber: "Uber",
  uber_car: "Uber Carro",
  uber_moto: "Uber Moto",
};

const ROUTE_MODE_OPTIONS = [
  { value: "auto", label: "Automatico (multimodal)" },
  { value: "walk", label: "A pe" },
  { value: "bike", label: "Bike" },
  { value: "car", label: "Carro" },
  { value: "moto", label: "Moto" },
  { value: "bus", label: "Onibus" },
  { value: "uber_car", label: "Uber Carro" },
  { value: "uber_moto", label: "Uber Moto" },
];

const ROUTE_RESTRICTION_OPTIONS = [
  { value: "none", label: "Sem restricao (deixa trocar modal)" },
  { value: "walk", label: "Forcar apenas A pe" },
  { value: "bike", label: "Forcar apenas Bike" },
  { value: "car", label: "Forcar apenas Carro" },
  { value: "moto", label: "Forcar apenas Moto" },
  { value: "bus", label: "Forcar apenas Onibus" },
  { value: "uber_car", label: "Forcar apenas Uber Carro" },
  { value: "uber_moto", label: "Forcar apenas Uber Moto" },
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

function normalizeValue(value, min, max) {
  const range = max - min;
  if (range === 0) {
    return 0.5;
  }
  return Math.max(0, Math.min(1, (value - min) / range));
}

function buildModeRanking(edges) {
  if (!edges?.length) {
    return [];
  }

  const grouped = new Map();

  for (const edge of edges) {
    const mode = edge?.modo || "desconhecido";
    const current = grouped.get(mode) || {
      modo: mode,
      distancia: 0,
      tempo: 0,
      custo: 0,
      risco: 0,
      quantidade: 0,
    };

    current.distancia += Number(edge?.distancia || 0);
    current.tempo += Number(edge?.tempo || 0);
    current.custo += Number(edge?.custo || 0);
    current.risco += Number(edge?.risco || 0);
    current.quantidade += 1;

    grouped.set(mode, current);
  }

  const list = [...grouped.values()].map((item) => ({
    ...item,
    risco_medio: item.quantidade > 0 ? item.risco / item.quantidade : 0,
  }));

  const times = list.map((item) => item.tempo);
  const costs = list.map((item) => item.custo);
  const risks = list.map((item) => item.risco_medio);

  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const minCost = Math.min(...costs);
  const maxCost = Math.max(...costs);
  const minRisk = Math.min(...risks);
  const maxRisk = Math.max(...risks);

  return list
    .map((item) => {
      const tempoNorm = normalizeValue(item.tempo, minTime, maxTime);
      const custoNorm = normalizeValue(item.custo, minCost, maxCost);
      const riscoNorm = normalizeValue(item.risco_medio, minRisk, maxRisk);
      const score = 0.5 * tempoNorm + 0.3 * custoNorm + 0.2 * riscoNorm;

      return {
        ...item,
        score,
      };
    })
    .sort((a, b) => a.score - b.score);
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
  const [selectedMode, setSelectedMode] = useState(ALL_MODES_KEY);
  const [selectedOptionId, setSelectedOptionId] = useState(null);
  const [routeModeChoice, setRouteModeChoice] = useState("auto");
  const [routeRestriction, setRouteRestriction] = useState("none");

  async function fetchRouteOptions() {
    setError("");
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/route`);

      if (!response.ok) {
        throw new Error(`Erro ao buscar rota (${response.status})`);
      }

      const routeData = await response.json();
      setOptionsPayload(wrapSingleRoute(routeData));
    } catch (err) {
      setError(err.message || "Falha ao carregar rota");
    } finally {
      setLoading(false);
    }
  }

  async function recalculate() {
    setError("");
    setRunning(true);
    try {
      const busOnlyRequested =
        routeRestriction === "bus" ||
        (routeRestriction === "none" && routeModeChoice === "bus");

      if (busOnlyRequested) {
        throw new Error(
          "Modo onibus requer dados GTFS em data/bus_gtfs (shapes.txt, trips.txt e routes.txt)."
        );
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

  const modeOptions = useMemo(() => {
    const modes = [...new Set(edges.map((edge) => edge?.modo).filter(Boolean))];
    return [ALL_MODES_KEY, ...modes];
  }, [edges]);

  useEffect(() => {
    if (selectedMode !== ALL_MODES_KEY && !modeOptions.includes(selectedMode)) {
      setSelectedMode(ALL_MODES_KEY);
    }
  }, [modeOptions, selectedMode]);

  const filteredEdges = useMemo(() => {
    if (selectedMode === ALL_MODES_KEY) {
      return edges;
    }
    return edges.filter((edge) => edge?.modo === selectedMode);
  }, [edges, selectedMode]);

  const filteredSegments = useMemo(() => {
    if (selectedMode === ALL_MODES_KEY) {
      return segments;
    }
    return segments.filter((segment) => segment?.modo === selectedMode);
  }, [segments, selectedMode]);

  const modeRanking = useMemo(() => buildModeRanking(edges), [edges]);

  const optionRanking = useMemo(() => {
    const valid = options.filter((option) => option.status === "ok");
    return valid
      .slice()
      .sort((a, b) => {
        const scoreA = typeof a.score === "number" ? a.score : 9999;
        const scoreB = typeof b.score === "number" ? b.score : 9999;
        return scoreA - scoreB;
      });
  }, [options]);

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
    if (filteredEdges.length > 0) {
      return getCenter(filteredEdges);
    }
    return getCenter(edges);
  }, [filteredEdges, edges]);

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div>
          <p className="eyebrow">Route Web</p>
          <h1>Visualizador de Rotas Multimodais</h1>
        </div>
        <div className="top-actions">
          <button onClick={fetchRouteOptions} disabled={loading || running}>
            Atualizar
          </button>
          <button className="primary" onClick={recalculate} disabled={running}>
            {running ? "Calculando..." : "Recalcular opcoes"}
          </button>
        </div>
      </header>

      <section className="route-controls">
        <div className="control-group">
          <label htmlFor="route-mode">Modal inicial</label>
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
          <label htmlFor="route-restriction">Restricao de modal</label>
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
          Para testar rota so de carro ou so de moto, selecione a restricao desejada e clique em Recalcular opcoes.
        </p>
      </section>

      {error ? <div className="error-box">{error}</div> : null}
      {!loading && !error && optionRanking.length === 0 && failedOptions.length > 0 ? (
        <div className="error-box">
          Nenhuma opcao de rota foi gerada no backend. Motivo: {firstErrorMessage}
        </div>
      ) : null}

      <main className="layout">
        <section className="map-panel">
          {loading ? (
            <div className="loading-state">Carregando rota...</div>
          ) : (
            <MapContainer center={center} zoom={13} className="map-area">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {filteredEdges.map((edge, index) => (
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
              <p>Distancia</p>
              <h2>{summary.distancia_total || 0} km</h2>
            </article>
            <article>
              <p>Risco medio</p>
              <h2>{summary.risco_medio || 0}</h2>
            </article>
            <article>
              <p>Esforco total</p>
              <h2>{Number(summary.esforco_total || 0).toFixed(3)} pts</h2>
            </article>
          </div>

          {selectedOption ? (
            <section className="selected-option-banner">
              <h3>Cenario selecionado</h3>
              <p>{selectedOption.label}</p>
              <small>
                Modal inicial: {MODAL_LABELS[selectedOption.modo_inicial] || selectedOption.modo_inicial}
                {selectedOption.restricao_modal
                  ? ` | Restricao: ${MODAL_LABELS[selectedOption.restricao_modal] || selectedOption.restricao_modal}`
                  : " | Sem restricao de modal"}
              </small>
            </section>
          ) : null}

          <section className="segments-list">
            <h3>Segmentos ({filteredSegments.length})</h3>
            {filteredSegments.length === 0 ? (
              <p>Nenhum segmento encontrado.</p>
            ) : (
              filteredSegments.map((segment, index) => (
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

          <section className="effort-panel info-section">
            <h3>Como o esforco e calculado</h3>
            <p>A pe: esforco = distancia (km) x 5.0 x fator de clima</p>
            <p>Bike: esforco = distancia (km) x 1.5 x fator de clima</p>
          </section>
        </aside>
      </main>
    </div>
  );
}

export default App;
