"""Cenários executados pelo endpoint /api/options."""

OPTION_SCENARIOS = [
    {"id": "multimodal_walk", "label": "Multimodal (a pe + trocas)", "modo_inicial": "walk", "restricao_modal": None},
    {"id": "walk_only", "label": "Todo a pe", "modo_inicial": "walk", "restricao_modal": "walk"},
    {"id": "bike_only", "label": "Somente bike", "modo_inicial": "bike", "restricao_modal": "bike"},
    {"id": "car_only", "label": "Somente carro", "modo_inicial": "car", "restricao_modal": "car"},
    {"id": "moto_only", "label": "Somente moto", "modo_inicial": "moto", "restricao_modal": "moto"},
    {"id": "bus_only", "label": "Somente onibus", "modo_inicial": "bus", "restricao_modal": "bus"},
    {"id": "bus_with_access", "label": "Onibus com acesso a pe", "modo_inicial": "walk", "restricao_modal": "bus_com_acesso"},
    {"id": "uber_car_only", "label": "Somente uber carro", "modo_inicial": "uber_car", "restricao_modal": "uber_car"},
    {"id": "uber_moto_only", "label": "Somente uber moto", "modo_inicial": "uber_moto", "restricao_modal": "uber_moto"},
]
