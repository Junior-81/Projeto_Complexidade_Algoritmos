# Documento Completo do Projeto (Versao Reduzida)

# Analise, Projeto e Complexidade de Algoritmos

# para Otimizacao de Rotas Multimodais no Recife

## 1. Introducao

O projeto implementa um sistema de recomendacao de rotas multimodais para Recife, equilibrando tempo, custo e risco. A proposta transforma um problema urbano real em um problema computacional de caminho minimo em grafo multimodal, com suporte a visualizacao e analise de cenarios.

A arquitetura atual possui tres camadas integradas:

- Motor Python de calculo de rotas
- Backend FastAPI para exposicao dos resultados
- Frontend React + Leaflet para visualizacao

## 2. Justificativa

A escolha de uma abordagem multiobjetivo responde a um problema real de mobilidade: a rota mais rapida nem sempre e a mais adequada quando se consideram custo e seguranca. O projeto e relevante por combinar modelagem em grafos, dados heterogeneos e comparacao entre algoritmos classicos (Dijkstra e A*), com foco em aplicacao urbana.

## 3. Objetivos

### 3.1 Objetivo Geral

Desenvolver e evoluir um sistema de roteamento multimodal para Recife, comparando Dijkstra e A* em criterios de tempo, custo e risco.

### 3.2 Objetivos Especificos

- Construir grafo multimodal com OSMnx
- Integrar dados de custo, risco, velocidade e GTFS
- Implementar busca multimodal com restricoes
- Expor o motor por API e interface web
- Permitir simulacao de cenarios e comparacao de resultados

## 4. Escopo Atual

O sistema esta funcional ponta a ponta: le entrada, carrega dados, calcula rota, gera saida estruturada e exibe no frontend. O fluxo principal inclui leitura de input, carga de CSVs, ajuste por clima, construcao/carregamento de grafo, execucao de Dijkstra ou A*, reconstrucao da rota e gravacao de output.

Ja implementado:

- Roteamento multimodal com 7 modais logicos
- Dijkstra e A* com restricoes de transicao
- Integracao GTFS com fallback
- API com calculo e ranking de opcoes
- Cache de grafo multimodal

Pontos pendentes:

- Testes automatizados e pipeline CI/CD
- Integracao efetiva do cache de base OSMnx no fluxo principal
- Uso completo de fatores de clima/mare por tabela
- Aplicacao de alagamento no peso final das arestas

## 5. Arquitetura e Modulos

O sistema separa responsabilidades entre carga de dados, modelagem de grafo, calculo de custo/risco, algoritmos de busca, reconstrucao de rota e exposicao por API/UI. Essa modularizacao facilita manutencao, evolucao e replicacao em outros contextos urbanos.

## 6. Metodologia

A metodologia foi incremental, com validacao continua. Cada etapa entrega um bloco funcional: dados, modelagem do grafo, funcao de custo multiobjetivo, busca e reconstrucao. A avaliacao combina duas perspectivas: tecnica (desempenho e estabilidade) e aplicada (impacto na mobilidade).

## 7. Base Tecnica do Modelo

O peso da aresta combina metricas normalizadas:

peso = 0.5 * tempo_norm + 0.3 * custo_norm + 0.2 * risco_norm

Tempo considera distancia, velocidade e fatores ambientais. Custo inclui componente financeiro e esforco fisico (principalmente caminhada e bike). Risco combina crime e acidente com ajustes por modal e clima. A normalizacao Min-Max permite comparar grandezas heterogeneas na mesma escala.

## 8. Dados Utilizados

O projeto utiliza dados de crime, acidentes, combustivel, velocidades, tarifas de referencia e GTFS. Tambem consulta clima em API externa e aplica fator de mare por heuristica. Parte dos dados carregados ainda esta em fase de consolidacao no calculo final.

## 9. Avaliacao de Desempenho e Escalabilidade

A avaliacao deve combinar complexidade teorica e experimentacao em cenarios simulados e reais. Indicadores recomendados: tempo de processamento por etapa, memoria, uso de CPU, latencia de resposta, custo total da rota, tempo total, risco medio e coerencia modal.

A comparacao entre Dijkstra e A* deve observar simultaneamente ganho computacional e qualidade da solucao. Para cobertura territorial, e recomendado usar analise origem-destino e monitorar estabilidade sob chuva, variacao de fluxo e eventos inesperados.

## 10. Impacto, Comparabilidade e Replicacao

Os indicadores de impacto incluem reducao de tempo de deslocamento, custo de viagem, exposicao a risco e melhoria de integracao com transporte publico. A comparacao com referencias nacionais e internacionais deve ser relativa ao contexto urbano e perfil de demanda.

A replicacao em outras cidades e viavel pela arquitetura modular, desde que haja adaptacao de dados locais, calibracao de pesos e validacao operacional. Para uso diario, variaveis como pesos, limiares de caminhada e parametros de custo dinamico devem ser recalibradas periodicamente.

## 11. Governanca e Maturidade

Ainda nao ha registro formal de consulta com especialistas e stakeholders. Essa etapa e recomendada para consolidar criterios de avaliacao e calibrar o modelo para uso real. O nivel de complexidade atual do projeto e medio-alto, com integracao de dados heterogeneos e busca multimodal, mas com boa capacidade de evolucao incremental.

## 12. Conclusao

O projeto ja entrega um ciclo funcional completo de recomendacao de rotas multimodais, com base tecnica consistente e potencial de aplicacao real. A consolidacao final depende, principalmente, de testes sistematicos, governanca de dados, validacao com usuarios e comparacoes experimentais mais amplas.