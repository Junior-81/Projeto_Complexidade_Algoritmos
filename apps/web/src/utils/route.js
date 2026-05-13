import { DEFAULT_CENTER, SEGMENT_DISPLAY_ORDER } from "../config/constants";

export function getCenter(edges) {
  if (!edges || edges.length === 0) return DEFAULT_CENTER;
  return edges[0]?.origem || DEFAULT_CENTER;
}

export function orderedSegmentEntries(segment) {
  const preferredEntries = SEGMENT_DISPLAY_ORDER
    .filter((key) => key in segment)
    .map((key) => [key, segment[key]]);

  const remainingEntries = Object.entries(segment).filter(
    ([key]) =>
      !SEGMENT_DISPLAY_ORDER.includes(key) && key !== "modo" && key !== "meio"
  );

  return [...preferredEntries, ...remainingEntries];
}

export function wrapSingleRoute(routeData) {
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
