"""Testes do endpoint POST /api/calculate e dos edge cases do SDD."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.entities.schemas import CalculateResponse
from app.main import app
from app.services import weights_service

client = TestClient(app)

# Origem/destino dentro da RM Recife (mesmo exemplo do SDD), em camelCase.
PAYLOAD_VALIDO = {
    "origin": [-8.062742, -34.8739],
    "destination": [-8.117809, -34.900231],
    "initialMode": "walk",
}


def test_calculate_retorna_estrutura_completa():
    """Payload valido -> 200 com edges/segments/summary/routePoints tipados."""
    resp = client.post("/api/calculate", json=PAYLOAD_VALIDO)
    assert resp.status_code == 200

    body = resp.json()
    # As chaves do JSON devem estar em camelCase.
    assert set(body.keys()) == {"edges", "segments", "summary", "routePoints"}
    assert "totalTime" in body["summary"]
    assert "averageSpeedKmh" in body["edges"][0]

    # A resposta deve casar exatamente com o schema de saida.
    data = CalculateResponse.model_validate(body)
    assert data.edges, "deve haver ao menos uma aresta"
    assert data.segments, "deve haver ao menos um segmento"
    assert data.route_points, "deve haver pontos de rota para plotagem"

    # Segmentos agrupam as arestas por modal.
    total_edges = sum(s.edge_count for s in data.segments)
    assert total_edges == len(data.edges)

    # Resumo soma os totais das arestas.
    assert data.summary.total_cost == pytest.approx(
        sum(e.cost for e in data.edges), abs=1e-4
    )

    # O segmento de onibus carrega os metadados GTFS.
    bus_segments = [s for s in data.segments if s.mode == "bus"]
    assert bus_segments and bus_segments[0].gtfs_validation is True
    assert bus_segments[0].line


def test_calculate_origem_fora_da_malha_retorna_400():
    """Coordenada isolada (fora do bounding box da RM Recife) -> 400."""
    payload = {**PAYLOAD_VALIDO, "origin": [-8.0, -34.0]}  # longitude no oceano
    resp = client.post("/api/calculate", json=payload)
    assert resp.status_code == 400
    assert "origin" in resp.json()["detail"].lower()


def test_calculate_payload_invalido_retorna_422():
    """initialMode invalido -> 422 (validacao estrita do Pydantic)."""
    payload = {**PAYLOAD_VALIDO, "initialMode": "teletransporte"}
    resp = client.post("/api/calculate", json=payload)
    assert resp.status_code == 422


def test_calculate_coordenada_malformada_retorna_422():
    """Origem sem longitude -> 422."""
    payload = {**PAYLOAD_VALIDO, "origin": [-8.062742]}
    resp = client.post("/api/calculate", json=payload)
    assert resp.status_code == 422


def test_weights_fallback_quando_banco_indisponivel():
    """Banco fora do ar -> pesos neutros, sem propagar erro (evita 500)."""

    class _FakeSession:
        def exec(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("conexao recusada"))

    mult = weights_service.get_edge_multipliers(_FakeSession(), "walk")
    assert mult.from_fallback is True
    assert mult.crime_factor == 1.0
    assert mult.flood_rain_multiplier == 1.0
    assert mult.speed_kmh == 5.0  # velocidade default de walk
