import {
  ROUTE_MODE_OPTIONS,
  ROUTE_RESTRICTION_OPTIONS,
} from "../config/constants";

export function RouteControls({
  routeModeChoice,
  routeRestriction,
  onChangeMode,
  onChangeRestriction,
  disabled,
}) {
  return (
    <section className="route-controls">
      <div className="control-group">
        <label htmlFor="route-mode">Modal inicial</label>
        <select
          id="route-mode"
          value={routeModeChoice}
          onChange={(event) => onChangeMode(event.target.value)}
          disabled={disabled}
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
          onChange={(event) => onChangeRestriction(event.target.value)}
          disabled={disabled}
        >
          {ROUTE_RESTRICTION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <p className="control-help">
        Para testar cenarios como carro/moto ou onibus com acesso a pe, selecione a
        restricao desejada e clique em Recalcular opcoes.
      </p>
    </section>
  );
}
