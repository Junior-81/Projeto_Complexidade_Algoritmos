function normalizeValue(value, min, max) {
  const range = max - min;
  if (range === 0) return 0.5;
  return Math.max(0, Math.min(1, (value - min) / range));
}

export function buildModeRanking(edges) {
  if (!edges?.length) return [];

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
      return { ...item, score };
    })
    .sort((a, b) => a.score - b.score);
}
