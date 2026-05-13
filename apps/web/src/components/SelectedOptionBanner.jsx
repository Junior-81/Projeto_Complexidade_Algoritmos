import { MODAL_LABELS } from "../config/constants";

export function SelectedOptionBanner({ option }) {
  if (!option) return null;

  const modal = MODAL_LABELS[option.modo_inicial] || option.modo_inicial;
  const restriction = option.restricao_modal
    ? ` | Restricao: ${MODAL_LABELS[option.restricao_modal] || option.restricao_modal}`
    : " | Sem restricao de modal";

  return (
    <section className="selected-option-banner">
      <h3>Cenario selecionado</h3>
      <p>{option.label}</p>
      <small>
        Modal inicial: {modal}
        {restriction}
      </small>
    </section>
  );
}
