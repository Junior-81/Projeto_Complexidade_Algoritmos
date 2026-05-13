import { useEffect, useState } from "react";

import {
  fetchCurrentRoute,
  fetchOptionsPayload,
  postCalculate,
} from "../api/routeApi";
import { wrapSingleRoute } from "../utils/route";

export function useRouteOptions() {
  const [optionsPayload, setOptionsPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setError("");
    setLoading(true);
    try {
      const data = await fetchOptionsPayload();
      setOptionsPayload(data);
    } catch (err) {
      try {
        const routeData = await fetchCurrentRoute();
        setOptionsPayload(wrapSingleRoute(routeData));
        setError(
          `Falha ao buscar opcoes; exibindo rota atual. Detalhe: ${
            err?.message || "erro desconhecido"
          }`
        );
      } catch (fallbackErr) {
        setError(fallbackErr.message || err.message || "Falha ao carregar rota");
      }
    } finally {
      setLoading(false);
    }
  }

  async function recalculate({ routeModeChoice, routeRestriction }) {
    setError("");
    setRunning(true);
    try {
      const isOfficialNoRestrictionMode =
        routeModeChoice === "auto" && routeRestriction === "none";

      if (isOfficialNoRestrictionMode) {
        try {
          const data = await fetchOptionsPayload();
          setOptionsPayload(data);
          return data?.best_option_id || null;
        } catch {
          const routeData = await postCalculate({
            modo_inicial: null,
            restricao_modal: null,
          });
          setOptionsPayload(wrapSingleRoute(routeData));
          setError(
            "Nao foi possivel carregar ranking de opcoes; exibindo rota sem restricao."
          );
          return null;
        }
      }

      const resolvedMode =
        routeModeChoice === "auto" && routeRestriction !== "none"
          ? routeRestriction
          : routeModeChoice;

      const routeData = await postCalculate({
        modo_inicial: resolvedMode === "auto" ? null : resolvedMode,
        restricao_modal: routeRestriction === "none" ? null : routeRestriction,
      });
      setOptionsPayload(wrapSingleRoute(routeData));
      return null;
    } catch (err) {
      setError(err.message || "Falha no recalculo");
      return null;
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return { optionsPayload, loading, running, error, refresh, recalculate };
}
