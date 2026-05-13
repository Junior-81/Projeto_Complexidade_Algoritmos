import { MapContainer, Polyline, Popup, TileLayer } from "react-leaflet";

import { MODAL_COLORS } from "../config/constants";
import { formatDuration, formatMoney } from "../utils/format";

export function RouteMap({ loading, center, edges }) {
  if (loading) {
    return <div className="loading-state">Carregando rota...</div>;
  }

  return (
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
  );
}
