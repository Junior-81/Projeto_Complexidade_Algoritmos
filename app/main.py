"""Ponto de entrada da aplicacao FastAPI."""

from fastapi import FastAPI

from app.controllers.routes import router as rotas_router

app = FastAPI(
    title="Motor de Rotas Multimodais - Recife",
    description=(
        "Backend de navegacao multimodal (caminhada, bicicleta, carro, moto, "
        "onibus, Uber) com pesos dinamicos a partir de fatores de crime, "
        "acidentes, alagamento, clima e mare."
    ),
    version="0.1.0",
)

app.include_router(rotas_router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    """Verificacao simples de disponibilidade da API."""
    return {"status": "ok"}
