# GUIA DE USO RÁPIDO - Sistema de Rotas Multimodais

## Instalação Rápida

```bash
# 1. Instale as dependências
pip install -r requirements.txt

# 2. Execute o sistema principal
python main.py
```

## Entrada (input.json)

O arquivo **input.json** deve ter este formato:

```json
{
  "origem": [-8.05, -34.90],
  "destino": [-8.10, -34.95],
  "modo_inicial": "walk"
}
```

### Parâmetros:

| Campo          | Descrição                             | Exemplo         |
| -------------- | ------------------------------------- | --------------- |
| `origem`       | Latitude e Longitude (lat, lon)       | [-8.05, -34.90] |
| `destino`      | Latitude e Longitude (lat, lon)       | [-8.10, -34.95] |
| `modo_inicial` | Modal inicial (walk\|bike\|car\|moto) | "walk"          |

**Notas:**
- Se modo_inicial = "walk": o sistema pode trocar para ônibus ou uber
- Se modo_inicial = "car", "moto" ou "bike": fica nesse modal

## Saída (output.json)

Após a execução, o arquivo **output.json** contém:

```json
{
  "rota": [
    {
      "modo": "walk",
      "origem": [-8.05, -34.90],
      "destino": [-8.06, -34.91],
      "tempo": 5.2,
      "distancia": 0.43,
      "custo": 0.0
    },
    {
      "modo": "bus",
      "origem": [-8.06, -34.91],
      "destino": [-8.10, -34.95],
      "tempo": 18.5,
      "distancia": 7.2,
      "custo": 4.50
    }
  ],
  "resumo": {
    "tempo_total": 23.7,
    "custo_total": 4.50,
    "distancia_total": 7.63,
    "risco_medio": 0.156
  }
}
```

### Interpretação dos Resultados:

- **rota**: Lista com cada segmento da viagem
  - `modo`: Tipo de transporte usado
  - `origem` / `destino`: Coordenadas lat/lon
  - `tempo`: Minutos
  - `distancia`: Quilômetros
  - `custo`: Reais (R$)

- **resumo**: Totalizações
  - `tempo_total`: Minutos de viagem
  - `custo_total`: Reais gastos
  - `distancia_total`: Quilômetros percorridos
  - `risco_medio`: Valor entre 0 (sem risco) e 1 (alto risco)

## Arquivos CSV Necessários

Todos os arquivos CSV devem estar na pasta `data/`:

| Arquivo                | Colunas                      | Descrição                  |
| ---------------------- | ---------------------------- | -------------------------- |
| crime_rate.csv         | mode, robberies              | Taxa de assaltos por modal |
| accident_rate.csv      | mode, deaths, involved       | Taxa de acidentes/veículos |
| transport_speed.csv    | mode, speed_kmh              | Velocidade média por modal |
| fuel_consumption.csv   | mode, km_per_liter           | Consumo de combustível     |
| uber_price_ranges.csv  | car_price_per_km             | Preço do Uber              |
| flood_risk_streets.csv | street_name, rain_multiplier | Ruas que alagam            |

## Algoritmo Utilizado

**A* (A-star)** com otimização multiobjetiva:

```
Função de custo = 0.5 × tempo_norm + 0.3 × custo_norm + 0.2 × risco_norm
```

Onde:
- `tempo_norm`: Tempo normalizado [0, 1]
- `custo_norm`: Custo normalizado [0, 1]
- `risco_norm`: Risco normalizado [0, 1]

## Exemplo Completo de Uso

### 1. Criar input.json:
```json
{
  "origem": [-8.05, -34.90],
  "destino": [-8.10, -34.95],
  "modo_inicial": "walk"
}
```

### 2. Executar:
```bash
python main.py
```

### 3. Verificar output.json:
```bash
# Linux/Mac:
cat output.json | jq

# Windows PowerShell:
Get-Content output.json | ConvertFrom-Json | ConvertTo-Json
```

## Limitações

❌ Dados de ônibus simulados (velocidade é aproximada)  
❌ Sem suporte a horários em tempo real  
❌ Sem otimização de "transfer" (troca de modal)  
❌ Grafo pode ser lento para cidades muito grandes  

## Próximas Melhorias

- [ ] Integração com GTFS real
- [ ] Cache de grafos
- [ ] Interface web
- [ ] Visualização em mapa
- [ ] Restrições por horário

---

**Veja README.md para documentação completa**
