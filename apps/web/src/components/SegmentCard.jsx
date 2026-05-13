import { MODAL_COLORS } from "../config/constants";
import { formatDuration, formatFieldValue, formatMoney, toLabel } from "../utils/format";
import { orderedSegmentEntries } from "../utils/route";

export function SegmentCard({ segment, index }) {
  return (
    <article className="segment-card">
      <header>
        <strong>
          {index + 1}. {segment.meio || segment.modo}
        </strong>
        <span
          className="chip"
          style={{ backgroundColor: MODAL_COLORS[segment.modo] || "#111111" }}
        >
          {segment.modo}
        </span>
      </header>

      <p className="segment-quick-view">
        {segment.distancia} km · {formatDuration(segment.tempo)} ·{" "}
        {formatMoney(segment.custo)} · {Number(segment.esforco || 0).toFixed(3)} pts
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
  );
}
