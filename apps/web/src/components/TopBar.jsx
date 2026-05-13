export function TopBar({ loading, running, onRefresh, onRecalculate }) {
  return (
    <header className="top-bar">
      <div>
        <p className="eyebrow">Route Web</p>
        <h1>Visualizador de Rotas Multimodais</h1>
      </div>
      <div className="top-actions">
        <button onClick={onRefresh} disabled={loading || running}>
          Atualizar
        </button>
        <button className="primary" onClick={onRecalculate} disabled={running}>
          {running ? "Calculando..." : "Recalcular opcoes"}
        </button>
      </div>
    </header>
  );
}
