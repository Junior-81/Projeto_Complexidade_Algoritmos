# Documento Completo do Projeto

# Analise, Projeto e Complexidade de Algoritmos

# para Otimizacao de Rotas Multimodais no Recife

## 1. Introducao

Este projeto implementa um sistema de recomendacao de rotas multimodais para Recife, com foco em otimizar deslocamentos considerando tempo, custo e risco. A proposta nasce da necessidade de traduzir um problema urbano cotidiano em um problema computacional tratavel, permitindo comparar diferentes estrategias de deslocamento com base em criterios objetivos. Em vez de retornar apenas um caminho curto, o sistema tenta representar melhor a realidade da viagem, considerando fatores economicos, operacionais e de seguranca.

No estado atual, a arquitetura foi pensada para separar claramente motor de calculo, servico de exposicao e camada de visualizacao. Essa separacao facilita evolucoes futuras, testes isolados e reaproveitamento do motor em outros canais alem da interface web. A arquitetura atual possui tres camadas principais:

- Motor de calculo em Python (arquivo principal main.py)
- Backend FastAPI (backend/app/main.py)
- Frontend React + Vite + Leaflet (frontend/)

O motor transforma o problema de mobilidade em caminho minimo em grafo multimodal. O grafo e construido a partir de OSMnx (malha viaria), enriquecido com dados CSV locais, GTFS de onibus e fatores climaticos em tempo de execucao.

## 2. Justificativa

A mobilidade urbana em Recife envolve variabilidade de transito, custo e seguranca. Em trajetos urbanos reais, a melhor rota nem sempre e a mais rapida, pois o usuario normalmente precisa equilibrar orcamento, previsibilidade e nivel de exposicao a risco. Por isso, a adocao de uma funcao multiobjetivo melhora a aderencia do sistema ao uso pratico.

Do ponto de vista de projeto e pesquisa aplicada, a iniciativa tambem e relevante porque integra diferentes fontes de dados, combina modelagem de grafos com heuristicas de roteamento e organiza essa logica em uma arquitetura reutilizavel. Isso permite tanto evolucao academica quanto aplicacao incremental no contexto local.

Do ponto de vista academico, o projeto e relevante por combinar:

- Modelagem de rede multimodal em grafo direcionado
- Algoritmos classicos de caminho minimo (Dijkstra e A*)
- Integracao de dados heterogeneos (CSV, API de clima, GTFS)
- Analise de normalizacao para combinar metricas com escalas distintas

## 3. Objetivos

### 3.1 Objetivo Geral

Desenvolver e evoluir um sistema multimodal de roteamento para Recife, com comparacao entre Dijkstra e A* e criterios de tempo, custo e risco.

Em termos praticos, o objetivo geral tambem inclui transformar o sistema em uma base solida para simulacao de cenarios de mobilidade, permitindo que ajustes de pesos, restricoes e dados sejam avaliados de forma controlada e reproduzivel.

### 3.2 Objetivos Especificos

Os objetivos especificos abaixo organizam a implementacao em frentes complementares: dados, modelagem, algoritmo, integracao e apresentacao. Essa divisao ajuda a manter clareza de escopo e facilita o acompanhamento de maturidade do projeto.

- Construir grafo multimodal da cidade com OSMnx
- Integrar dados de risco (crime e acidente), custo e velocidade
- Integrar trechos de onibus via GTFS
- Implementar e comparar Dijkstra e A* no mesmo modelo de custo
- Expor o motor por API REST para consumo no frontend
- Permitir simulacao de cenarios de modal e restricoes
- Gerar saidas interpretaveis por aresta, segmento e resumo

## 4. Escopo Atual do Sistema (Estado Real)

O projeto esta funcional, porem ainda em fase de consolidacao tecnica. Atualmente, ja e possivel executar o fluxo completo do calculo, inspecionar os resultados via API e visualizar a rota no frontend, o que caracteriza um produto funcional para validacao. Ao mesmo tempo, ainda existem lacunas esperadas para uma versao final mais robusta, principalmente em testes automatizados, padronizacao de experimentos e fechamento de algumas integracoes de dados.

O fluxo principal em producao local e:

1. Leitura de input.json
2. Carga de CSVs em data/
3. Calculo de perfis de risco por modal
4. Configuracao de calculo de custo
5. Consulta de clima (Open-Meteo) e fator de mare heuristico
6. Carregamento/construcao de grafo multimodal (com cache ativo)
7. Integracao GTFS para onibus
8. Calculo de parametros Min-Max para normalizacao
9. Execucao de Dijkstra ou A*
10. Reconstrucao da rota em edges e segments
11. Persistencia em output.json

### 4.1 O que ja esta implementado

Nesta etapa do projeto, os componentes essenciais de ponta a ponta estao presentes e conectados. Isso permite executar cenarios reais e comparar estrategias de rota de forma consistente.

- Motor multimodal com 7 modais logicos: walk, bike, car, moto, bus, uber_car, uber_moto
- Algoritmos Dijkstra e A* com estado estendido para restricao de uso de onibus
- Funcao de custo unificada com pesos fixos
- Integracao GTFS stop-based (stops + stop_times + trips + routes) com fallback shape-based
- API com endpoints de saude, calculo direto e ranking de opcoes
- Frontend com mapa, filtros por modal, ranking de cenarios e detalhes por segmento
- Cache do grafo multimodal validado por hash dos dados

### 4.2 O que ainda nao esta finalizado

As pendencias abaixo nao impedem o funcionamento atual, mas impactam confiabilidade, manutencao e capacidade de evolucao do projeto no longo prazo. Elas representam, portanto, os principais pontos de fechamento para uma entrega mais madura.

- Nao ha suite de testes automatizados (unitarios/integracao/performance)
- Nao ha pipeline CI/CD
- Cache de base_graph OSMnx esta utilitario pronto, mas nao integrado no fluxo principal
- weather_factors.csv e tide_factors.csv sao carregados, mas hoje o fator vem de regra em codigo (nao dos CSVs)
- flood_risk_streets.csv e carregado, mas multiplicadores de alagamento ainda nao entram no peso final das arestas
- Nao ha monitoramento de qualidade de rota/tempo por lote de cenarios

## 5. Arquitetura e Relacao entre Modulos

### 5.1 Camada de Entrada e Dados

- loaders/csv_loader.py: carrega todos os CSVs esperados
- loaders/weather_api.py: busca precipitacao na Open-Meteo e calcula fator de chuva

### 5.2 Camada de Modelagem de Grafo

- graph/graph_builder.py:
  - carrega malha viaria com OSMnx
  - replica arestas para modais
  - incorpora velocidade OSM (maxspeed) para modais motorizados
  - integra GTFS adicionando nos de parada e arestas bus
  - salva/carrega cache de grafo multimodal
- graph/normalizer.py: calcula min, max e range para tempo, custo e risco
- graph/risk_calculator.py: gera risco por modal a partir de crime + acidente
- graph/cost_calculator.py: calcula custo financeiro e esforco fisico

### 5.3 Camada de Roteamento

- routing/dijkstra_multimodal.py: busca de menor custo acumulado
- routing/astar_multimodal.py: busca guiada por heuristica
- routing/path_reconstructor.py:
  - reconstrucao detalhada das arestas
  - agregacao de segmentos por modal
  - consolidacao do resumo
- routing/uber_segment_aggregator.py: agrupa corrida Uber para evitar dupla cobranca por aresta

### 5.4 Camada de Exposicao

- backend/app/main.py:
  - GET /api/health
  - GET /api/route
  - POST /api/calculate
  - POST /api/options
  - executa main.py via subprocess
- frontend/src/App.jsx:
  - requisita opcoes e rotas
  - exibe polylines por modal
  - exibe ranking de cenarios
  - permite recalculo com modo inicial e restricoes

## 6. Metodologia Aplicada no Projeto

A metodologia foi estruturada em etapas incrementais para permitir validacao continua do sistema. Em vez de esperar uma implementacao totalmente completa para testar, cada fase entrega um bloco funcional que se conecta ao proximo. Isso reduziu risco de retrabalho e facilitou a observacao dos efeitos de cada decisao de modelagem.

Tambem foi adotada uma logica de avaliacao em dois planos: um plano tecnico (desempenho computacional, qualidade da rota, estabilidade em variacoes de entrada) e um plano aplicado (impacto no deslocamento, cobertura territorial, possibilidade de adocao operacional). Essa combinacao evita que o projeto seja avaliado apenas por tempo de processamento ou apenas por impressao qualitativa de uso.

## Etapa 1 - Coleta e Estruturacao de Dados

Dados CSV e GTFS sao organizados em data/ e lidos no inicio do fluxo. Dados climaticos sao complementados por API externa.

Nesta fase, o foco e garantir consistencia de entrada e rastreabilidade das fontes, pois a qualidade da recomendacao final depende diretamente da qualidade e cobertura desses dados.

## Etapa 2 - Modelagem em Grafo Multimodal

A rede viaria e transformada em MultiDiGraph, com arestas replicadas por modal e metadados de distancia e velocidade.

Essa modelagem cria uma base comum para comparar modais diferentes no mesmo espaco de busca, permitindo que o algoritmo avalie trocas de meio de transporte de forma padronizada.

## Etapa 3 - Definicao da Funcao Multiobjetivo

Tempo, custo e risco sao calculados por aresta, normalizados por Min-Max e combinados em peso unico.

Com isso, o processo de decisao deixa de depender de uma unica variavel e passa a refletir um compromisso entre eficiencia, gasto e seguranca, alinhado ao comportamento esperado em cenarios urbanos.

## Etapa 4 - Busca de Caminho e Reconstrucao

Dijkstra ou A* encontram a sequencia de estados; em seguida a rota e reconstruida em estruturas detalhadas para consumo da API/UI.

A reconstrucao final e importante para transformar o resultado do algoritmo em informacao acionavel para o usuario, com segmentos legiveis e resumo consolidado da viagem.

## 7. Detalhamento Tecnico (Algoritmos, Pesos, Normalizacao e Dados)

### 7.1 Estado de Busca

Nos dois algoritmos, o estado interno inclui:

- node_id
- modal_atual
- used_bus (flag booleana)

Isso permite impor restricoes como bus_com_acesso (rota valida apenas se usar bus em algum trecho).

### 7.2 Funcao de Peso da Aresta

A funcao aplicada em Dijkstra e A* e:

peso = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm

Onde:

- tempo_norm = normalizacao Min-Max do tempo do trecho
- custo_norm = normalizacao Min-Max do custo de roteamento
- risco_norm = normalizacao Min-Max do risco do trecho

Regras adicionais:

- Em restricao de onibus com acesso, aresta walk pode receber penalidade multiplicativa (walk_penalty_factor, ex. 1.4)
- Pode haver limite de distancia por aresta walk (ex. 0.5 km)

### 7.3 Calculo de Tempo

- Distancia da aresta: distance_km
- Velocidade:
  - motorizados: prioridade para osm_speed_kmh da aresta
  - demais: velocidade de tabela (transport_speed.csv)
- Tempo base: distance_km / velocidade
- Ajuste ambiental: tempo_final = tempo_base * rain_factor * tide_factor

### 7.4 Calculo de Custo

Em graph/cost_calculator.py:

- walk: custo financeiro 0
- bike: custo operacional por km (fixed_cost_per_km)
- bus: tarifa fixa (R$ 4.50)
- car/moto: consumo (km_per_liter) x preco combustivel
- uber_car/uber_moto: tarifa dinamica por base + km + minuto

Formula Uber:

preco = base + (distancia_km * price_per_km) + (tempo_min * price_per_min)

Tarifas variam por surge_index, composto por:

- clima (rain_factor)
- transito inferido por velocidade media
- oferta de motorista por heuristica de horario

### 7.5 Custo de Roteamento e Esforco

O roteamento usa custo financeiro + esforco fisico ponderado:

custo_rota = custo_financeiro + (effort_weight * effort_score)

Esforco:

- walk: distancia_km * 5.0 * climate_factor
- bike: distancia_km * 1.5 * climate_factor
- demais: 0

### 7.6 Calculo de Risco

RiskCalculator combina:

- crime_risk = robberies / max_robberies
- accident_risk = deaths / involved

Composicao por modal:

risco_base_modal = 0.5 * crime_risk + 0.5 * accident_risk

Depois aplica:

- normalizacao geral se max_risk > 1
- safety multipliers por modal
- climate_factor
- acumulacao por distancia (risco_final = risco_ajustado * distancia_km / 10)

### 7.7 Normalizacao Min-Max

normalizado = (valor - min) / (max - min)

- Min/max sao obtidos por amostragem de ate 80k arestas do grafo
- Se range = 0, normalizer retorna 0.5 para manter estabilidade

### 7.8 Heuristica do A*

A* usa estimativa baseada em distancia em linha reta entre no atual e destino, dividida pela maior velocidade disponivel. Depois normaliza para escala da funcao de custo.

### 7.9 Restricoes de Transicao de Modal

Quando o modo inicial e walk:

- transicao permitida de walk para: walk, bus, uber_car, uber_moto, bike
- de modal motorizado/publico de volta para walk para concluir percurso
- transicoes para car/moto proprios sao bloqueadas nesse contexto

### 7.10 Integracao GTFS

Prioridade atual:

1. Stop-based (stops + stop_times)
2. Fallback shape-based

No stop-based:

- cria nos de parada (tipo stop)
- conecta rua <-> parada com arestas walk dentro de raio
- cria arestas bus entre paradas consecutivas por trip

### 7.11 Ranking de Cenarios na API

No endpoint /api/options:

- roda multiplos cenarios predefinidos
- normaliza tempo_total, custo_total e risco_medio entre cenarios validos
- score final usa mesmos pesos (0.5, 0.3, 0.2)
- regra de negocio favorece recomendacao de 1 modal vencedor em cenarios sem restricao

## 8. Dados Considerados pelo Sistema

### 8.1 CSVs efetivamente usados

- crime_rate.csv: mode, robberies
- accident_rate.csv: mode, deaths, involved
- fuel_consumption.csv: mode, km_per_liter, fixed_cost_per_km
- uber_price_ranges.csv: service, base_fare, km_min, km_max, min_min, min_max
- transport_speed.csv: mode, speed_kmh
- flood_risk_streets.csv: street_name, rain_multiplier, tide_multiplier (carregado)

### 8.2 Dados carregados para extensao

- weather_factors.csv (fatores por condicao)
- tide_factors.csv (fatores por nivel de mare)

Obs: no estado atual, fatores de chuva e mare usados no calculo vem de logica no codigo, nao de lookup direto nesses dois CSVs.

### 8.3 GTFS

Arquivos lidos no fluxo GTFS:

- stops.txt
- stop_times.txt
- trips.txt
- routes.txt
- fallback adicional por shapes.txt

## 9. Complexidade Computacional (Visao Pratica)

- Construcao do grafo multimodal: custo alto na primeira execucao (dependente de OSM + replicacao de arestas + GTFS)
- Dijkstra: ordem classica O(E log V) com fila de prioridade
- A*: depende da heuristica; em geral expande menos estados que Dijkstra
- Reconstrucao de rota: linear no tamanho do caminho encontrado

Com cache multimodal ativo, o gargalo de carregamento reduz significativamente apos a primeira rodada.

## 10. Riscos Tecnicos e Pontos de Atencao

- Inconsistencia potencial entre restricao de modal da entrada e rota final, devendo ser coberta por testes
- Dependencia de chamada externa para clima (Open-Meteo)
- Ausencia de testes automatizados para regressao em regras de transicao modal
- Arquivos de cache podem crescer e exigir estrategia de limpeza/versionamento

## 11. Cronograma Sugerido para Conclusao

O cronograma foi proposto como uma trilha de consolidacao tecnica. A ideia e priorizar primeiro confiabilidade e cobertura de testes, depois fechar integracoes pendentes e, por fim, formalizar comparacoes de desempenho e documentacao final.

Mes 1

- Criar testes unitarios para cost_calculator, risk_calculator e normalizer
- Criar testes de integracao para Dijkstra e A* com cenarios pequenos

Mes 2

- Integrar cache de base_graph OSMnx no fluxo principal
- Aplicar flood_risk_streets no calculo final de tempo/risco por aresta

Mes 3

- Consolidar uso de weather_factors.csv e tide_factors.csv no lugar de regras fixas
- Adicionar validacoes de consistencia de modal (entrada x saida)

Mes 4

- Benchmark formal Dijkstra vs A* em multiplas distancias/horarios
- Consolidar documentacao final e checklist de entrega

Mes 5 (recomendado)

- Realizar entrevistas com stakeholders (usuarios, tecnicos e gestores de mobilidade)
- Consolidar calibracao de pesos e criterios com base nas percepcoes coletadas

## 12. Avaliacao Integrada de Desempenho, Impacto e Escalabilidade

A avaliacao do projeto deve combinar analise teorica de complexidade com experimentacao em dados reais e simulados. No plano teorico, Dijkstra e A* podem ser examinados pela relacao entre vertices e arestas do grafo. No plano pratico, o que interessa e observar o custo de execucao em cenarios de mobilidade com diferentes distancias, modos e restricoes, verificando tempo total de processamento, memoria consumida e estabilidade do resultado retornado.

Para reduzir risco metodologico, os algoritmos devem ser testados em ambiente controlado e em cenarios mais proximos de operacao real. A simulacao permite comparar condicoes equivalentes e medir se houve ganho de tempo de calculo sem perda de qualidade de rota. Ja os testes com variabilidade real (chuva, maré, mudanca de fluxo e incidentes) permitem avaliar robustez e tempo de resposta da API sob mudancas inesperadas de contexto.

Sob a perspectiva de infraestrutura, o sistema pode registrar tempo por etapa (leitura, construcao de grafo, busca e reconstrucao), uso de CPU e memoria, numero de estados expandidos e latencia media de resposta. Como o projeto nao foi desenhado para GPU, a metrica de GPU e tratada como nao aplicavel no estado atual. Em termos de escalabilidade, o principal criterio e manter crescimento controlado do tempo de resposta conforme aumenta a quantidade de consultas e de cenarios processados por lote.

No aspecto de qualidade da solucao, o projeto pode ser avaliado por custo total da rota, tempo total, risco medio e coerencia modal do percurso sugerido. Para isso, e recomendado avaliar erros de predicao comparando estimativas com tempos observados, alem de usar analise origem-destino para verificar cobertura territorial, identificando regioes com melhor ou pior desempenho do algoritmo.

## 13. Indicadores de Impacto Urbano e Comparabilidade

Os indicadores de impacto devem refletir resultados operacionais e sociais. Entre os principais estao reducao do tempo de deslocamento, reducao de custo monetario por viagem, reducao de exposicao a risco, aumento de acesso ao transporte publico, continuidade de caminhabilidade e maior integracao entre modais. Em conjunto, esses indicadores mostram se a rota otimizada melhora apenas o calculo ou melhora, de fato, a experiencia de deslocamento.

Para facilitar comparacoes justas entre criterios heterogeneos, o projeto usa normalizacao Min-Max nas metricas de tempo, custo e risco. Esse escalonamento multidimensional torna as variaveis comparaveis na mesma faixa e evita que uma unica grandeza domine o resultado final apenas por escala numerica. A escolha de pesos funciona, assim, como regra explicita de priorizacao de variaveis financeiras, espaciais e operacionais.

Na comparacao com referencias nacionais e internacionais, a avaliacao pode usar indicadores equivalentes de mobilidade, como tempo medio de viagem, custo medio por km, participacao modal e nivel de acessibilidade. A interpretacao recomendada e relativa, isto e, por semelhanca de contexto urbano e perfil de demanda, e nao por comparacao absoluta de cidades com estruturas muito diferentes.

## 14. Replicabilidade, Viabilidade e Governanca de Decisao

A replicacao para outros contextos urbanos e viavel porque o projeto separa regras de calculo e fontes de dados. Em outro municipio, a adaptacao envolve substituir bases locais de velocidade, risco, tarifas e transporte publico, recalibrar pesos e validar a consistencia das fontes. Essa abordagem reduz acoplamento e aumenta reuso da arquitetura.

Do ponto de vista economico e ambiental, a viabilidade depende do custo de manutencao dos dados, da confiabilidade das integracoes externas e do potencial de reduzir deslocamentos ineficientes e uso excessivo de modais mais poluentes. A avaliacao ambiental e social pode ser reforcada medindo variacao de distancia percorrida, incentivo ao transporte coletivo, melhoria de conectividade e reducao de exposicao em trechos mais inseguros.

No estado atual, nao ha registro formal de consulta com especialistas e stakeholders. Portanto, os criterios vigentes foram definidos tecnicamente. Para uma fase de adocao diaria, recomenda-se entrevistar tecnicos de mobilidade, gestores publicos e usuarios para validar: pesos da funcao objetivo, limites de caminhada, tolerancia a trocas de modal, criterios de seguranca e expectativas de tempo de resposta. Esses insumos sao essenciais para alinhar o modelo com o uso real.

Em um cenario de operacao cotidiana, algumas variaveis devem ser candidatas a substituicao ou recalibracao periodica, como pesos da funcao objetivo, fatores climaticos, parametros de custo dinamico e regras de transicao modal. Esse ajuste continuo aumenta aderencia local e reduz dependencia de heuristicas fixas.

Quanto ao nivel de complexidade, a avaliacao consolidada deste projeto e de complexidade medio-alta: ha integracao de dados heterogeneos, busca multimodal com restricoes, normalizacao de criterios conflitantes e camada completa de API/interface. Ainda assim, a estrutura modular mantem viabilidade de manutencao e evolucao incremental.

## 15. Referencias Tecnicas e de Implementacao

- OSMnx e OpenStreetMap para modelagem da rede viaria
- NetworkX para grafo e busca
- FastAPI para camada HTTP
- React + Leaflet para visualizacao
- GTFS para integracao de rede de onibus

## 16. Conclusao

O projeto ja possui uma base tecnica consistente e funcional para roteamento multimodal em Recife, com algoritmo, modelagem de dados, API e interface integrados. Isso significa que o ciclo principal de valor ja existe: receber entrada, calcular rota por criterios multiplos, retornar resultado estruturado e apresentar visualmente ao usuario.

Ao mesmo tempo, o estado atual pode ser classificado como funcional em evolucao: a espinha dorsal esta pronta, mas faltam etapas de robustez para consolidar uma versao final de producao e de avaliacao academica mais rigorosa. Os proximos ganhos relevantes estao concentrados em testes, governanca de dados, consulta a stakeholders e validacao comparativa sistematica entre cenarios e algoritmos.
