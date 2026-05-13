"""Parse de `restricao_modal` em parâmetros consumidos pela busca."""

from dataclasses import dataclass


@dataclass
class ModalRestriction:
    allowed_modes: set[str] | None = None
    bus_required: bool = False
    max_walk_distance_km: float | None = None
    walk_penalty_factor: float = 1.0


def parse(restricao_modal: str | None) -> ModalRestriction:
    if not restricao_modal:
        return ModalRestriction()

    key = str(restricao_modal).lower()

    if key in {"bus", "bus_com_acesso"}:
        return ModalRestriction(
            allowed_modes={"walk", "bus"},
            bus_required=True,
            max_walk_distance_km=0.5,
            walk_penalty_factor=1.4,
        )

    if key == "bus_estrito":
        return ModalRestriction(allowed_modes={"bus"})

    return ModalRestriction(allowed_modes={key})
