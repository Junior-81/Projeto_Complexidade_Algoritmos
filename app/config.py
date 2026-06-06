"""Configuracoes da aplicacao, carregadas de variaveis de ambiente / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parametros de execucao do backend de rotas."""

    # Conexao SQLAlchemy/psycopg com o PostgreSQL.
    database_url: str = "postgresql+psycopg://rotas:rotas@localhost:5433/rotas_recife"

    # Pasta onde estao os CSVs de fatores e o feed GTFS (note: data/data).
    data_dir: str = "data/data"

    # Tempo maximo permitido para o calculo de uma rota (edge case de timeout).
    graph_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
