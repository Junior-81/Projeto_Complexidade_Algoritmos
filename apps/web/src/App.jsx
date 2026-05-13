import { useEffect, useMemo, useState } from "react";

import { EffortPanel } from "./components/EffortPanel";
import { RouteControls } from "./components/RouteControls";
import { RouteMap } from "./components/RouteMap";
import { SegmentsList } from "./components/SegmentsList";
import { SelectedOptionBanner } from "./components/SelectedOptionBanner";
import { SummaryGrid } from "./components/SummaryGrid";
import { TopBar } from "./components/TopBar";
import { ALL_MODES_KEY } from "./config/constants";
import { useRouteOptions } from "./hooks/useRouteOptions";
import { getCenter } from "./utils/route";

function App() {
  const { optionsPayload, loading, running, error, refresh, recalculate } =
    useRouteOptions();

  const [selectedMode, setSelectedMode] = useState(ALL_MODES_KEY);
  const [selectedOptionId, setSelectedOptionId] = useState(null);
  const [routeModeChoice, setRouteModeChoice] = useState("auto");
  const [routeRestriction, setRouteRestriction] = useState("none");

  const options = optionsPayload?.options || [];

  useEffect(() => {
    if (options.length === 0) return;

    const hasSelected = options.some((option) => option.id === selectedOptionId);
    if (hasSelected) return;

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
    if (selectedMode === ALL_MODES_KEY) return edges;
    return edges.filter((edge) => edge?.modo === selectedMode);
  }, [edges, selectedMode]);

  const filteredSegments = useMemo(() => {
    if (selectedMode === ALL_MODES_KEY) return segments;
    return segments.filter((segment) => segment?.modo === selectedMode);
  }, [segments, selectedMode]);

  const failedOptions = useMemo(
    () => options.filter((option) => option.status === "error"),
    [options]
  );

  const optionRanking = useMemo(
    () =>
      options
        .filter((option) => option.status === "ok")
        .slice()
        .sort((a, b) => {
          const scoreA = typeof a.score === "number" ? a.score : 9999;
          const scoreB = typeof b.score === "number" ? b.score : 9999;
          return scoreA - scoreB;
        }),
    [options]
  );

  const firstErrorMessage = useMemo(() => {
    if (failedOptions.length === 0) return "";
    const first = failedOptions[0];
    return (
      first?.error?.message ||
      first?.error?.stderr ||
      "Falha ao calcular as opcoes de rota."
    );
  }, [failedOptions]);

  const center = useMemo(() => {
    if (filteredEdges.length > 0) return getCenter(filteredEdges);
    return getCenter(edges);
  }, [filteredEdges, edges]);

  async function handleRecalculate() {
    const bestId = await recalculate({ routeModeChoice, routeRestriction });
    if (bestId) {
      setSelectedOptionId(bestId);
    }
  }

  return (
    <div className="app-shell">
      <TopBar
        loading={loading}
        running={running}
        onRefresh={refresh}
        onRecalculate={handleRecalculate}
      />

      <RouteControls
        routeModeChoice={routeModeChoice}
        routeRestriction={routeRestriction}
        onChangeMode={setRouteModeChoice}
        onChangeRestriction={setRouteRestriction}
        disabled={running}
      />

      {error ? <div className="error-box">{error}</div> : null}
      {!loading && !error && optionRanking.length === 0 && failedOptions.length > 0 ? (
        <div className="error-box">
          Nenhuma opcao de rota foi gerada no backend. Motivo: {firstErrorMessage}
        </div>
      ) : null}

      <main className="layout">
        <section className="map-panel">
          <RouteMap loading={loading} center={center} edges={filteredEdges} />
        </section>

        <aside className="info-panel">
          <SummaryGrid summary={summary} />
          <SelectedOptionBanner option={selectedOption} />
          <SegmentsList segments={filteredSegments} />
          <EffortPanel />
        </aside>
      </main>
    </div>
  );
}

export default App;
