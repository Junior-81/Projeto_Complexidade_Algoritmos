"""Engine e sessao do SQLAlchemy/SQLModel (stack sincrona)."""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# `pool_pre_ping` evita usar conexoes mortas; util quando o Postgres reinicia.
engine = create_engine(settings.database_url, pool_pre_ping=True)


def init_db() -> None:
    """Cria as tabelas a partir dos modelos SQLModel.

    Em producao usamos Alembic (`alembic upgrade head`); este helper existe
    para testes e execucoes locais rapidas sem migracoes.
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency do FastAPI que fornece uma Session por requisicao.

    Importante: a sessao e aberta de forma preguicosa. Se o Postgres estiver
    indisponivel, a falha so acontece quando uma query e executada — e a camada
    de servico (`weights_service`) trata isso com pesos neutros, evitando 500.
    """
    with Session(engine) as session:
        yield session
