import { SegmentCard } from "./SegmentCard";

export function SegmentsList({ segments }) {
  return (
    <section className="segments-list">
      <h3>Segmentos ({segments.length})</h3>
      {segments.length === 0 ? (
        <p>Nenhum segmento encontrado.</p>
      ) : (
        segments.map((segment, index) => (
          <SegmentCard
            key={`${segment.modo}-${index}`}
            segment={segment}
            index={index}
          />
        ))
      )}
    </section>
  );
}
