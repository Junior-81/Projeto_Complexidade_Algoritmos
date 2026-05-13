import { formatDuration, formatMoney } from "../utils/format";

export function SummaryGrid({ summary }) {
  return (
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
  );
}
