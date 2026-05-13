"""Modelos Pydantic dos payloads das rotas."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from core.config import VALID_ALGORITHMS


class CalculateRequest(BaseModel):
    origem: list[float] | None = Field(default=None, description="[lat, lon]")
    destino: list[float] | None = Field(default=None, description="[lat, lon]")
    modo_inicial: str | None = Field(default=None)
    algoritmo: str | None = Field(default=None, description="dijkstra|astar")
    restricao_modal: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_coordinates(self) -> "CalculateRequest":
        for field_name in ("origem", "destino"):
            coords = getattr(self, field_name)
            if coords is None:
                continue
            if len(coords) != 2:
                raise ValueError(f"{field_name} precisa ter 2 valores: [lat, lon]")
        if self.algoritmo is not None and self.algoritmo not in VALID_ALGORITHMS:
            raise ValueError("algoritmo deve ser dijkstra ou astar")
        return self


class OptionsRequest(BaseModel):
    algoritmo: str | None = Field(default=None, description="dijkstra|astar")

    @model_validator(mode="after")
    def validate_algorithm(self) -> "OptionsRequest":
        if self.algoritmo is not None and self.algoritmo not in VALID_ALGORITHMS:
            raise ValueError("algoritmo deve ser dijkstra ou astar")
        return self
