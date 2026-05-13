"""Pacote core — orquestração do motor de roteamento.

Para evitar carregar dependências pesadas (`pandas`, `osmnx`, etc.) só por
importar `core.config` ou `core.restrictions`, o re-export de `run_route` é
lazy. Use diretamente:

    from core.pipeline import run_route
"""
