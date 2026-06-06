"""Controller HTTP do motor de rotas (camada FastAPI)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.entities.schemas import CalculateRequest, CalculateResponse
from app.services import routing_service
from app.services.routing_service import (
    CalculoTimeoutError,
    PontoForaDaMalhaError,
    RotaNaoEncontradaError,
)

router = APIRouter(prefix="/api", tags=["rotas"])


@router.post("/calculate", response_model=CalculateResponse)
def calculate(
    req: CalculateRequest,
    session: Session = Depends(get_session),
) -> CalculateResponse:
    """Calcula a melhor rota multimodal entre origem e destino.

    Edge cases tratados:
      * 400 -> origem/destino fora da malha viaria;
      * 404 -> nao existe caminho conectando os pontos;
      * 408 -> o calculo ultrapassou o tempo maximo (10s);
      * 422 -> payload invalido (validacao automatica do Pydantic);
      * banco indisponivel nao gera 500 (pesos neutros no servico).
    """
    try:
        return routing_service.calculate(req, session)
    except PontoForaDaMalhaError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except RotaNaoEncontradaError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CalculoTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=str(exc)
        ) from exc
