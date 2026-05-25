# Escopo do Projeto: Análise, Projeto e

# Complexidade de Algoritmos para Otimização

# de Rotas Multimodais no Recife

## 1. Introdução

A mobilidade urbana é um dos desafios mais complexos das grandes cidades
contemporâneas. Em Recife, capital de Pernambuco, essa questão é
particularmente crítica, com a cidade frequentemente listada entre as mais
congestionadas do Brasil e do mundo [1]. O deslocamento entre pontos estratégicos
da cidade, como o Cine São Luiz, na rua da Aurora, no centro, e a Faculdade Nova
Roma, na rua Padre Carapuceiro, em Boa Viagem, evidencia a necessidade de
soluções eficientes para otimizar o tempo e os recursos dos cidadãos.

Este projeto propõe a análise, o projeto e a avaliação da complexidade de
algoritmos para a otimização de rotas multimodais entre esses dois pontos,
considerando as particularidades do sistema de transporte do Recife. O objetivo é
desenvolver um modelo computacional que possa identificar a rota ótima (ou um
conjunto de rotas ótimas) com base em múltiplos critérios, como tempo de
deslocamento, custo, impacto ambiental e preferência do usuário.

O estudo se concentrará em uma abordagem multimodal, integrando diferentes
modais de transporte, como ônibus, metrô, BRT (Bus Rapid Transit), transporte por
aplicativo, bicicleta e deslocamento a pé. A análise levará em conta fatores
dinâmicos, como variações de tráfego em diferentes horários do dia, disponibilidade
de transporte público e condições das vias.

## 2. Justificativa

A crescente urbanização e a concentração de atividades econômicas em grandes
centros urbanos têm levado a um aumento significativo da demanda por transporte,
resultando em congestionamentos, poluição e perda de qualidade de vida. A
otimização de rotas em redes de transporte multimodais é um problema complexo
que tem sido objeto de intensa pesquisa na área de ciência da computação e
engenharia de transportes [2, 3].

No contexto do Recife, a complexidade do sistema de transporte, com suas vias
congestionadas, a integração entre diferentes modais e as características
geográficas da cidade, torna o problema ainda mais desafiador. A implementação
de um sistema de recomendação de rotas multimodais eficiente pode trazer
benefícios significativos para a população, como a redução do tempo de viagem, a
diminuição dos custos de transporte e a promoção de modais mais sustentáveis.

Este projeto se justifica pela necessidade de aplicar o conhecimento teórico da área
de análise e projeto de algoritmos para resolver um problema real e de grande
impacto para a cidade do Recife. A pesquisa contribuirá para o avanço do


conhecimento na área de otimização de rotas urbanas e poderá servir de base para
o desenvolvimento de soluções tecnológicas inovadoras para a mobilidade urbana.

## 3. Objetivos

### 3.1. Objetivo Geral

Desenvolver e analisar algoritmos para a otimização de rotas multimodais entre a
Avenida Conde da Boa Vista e a Rua Padre Carapuceiro, no Recife, considerando
múltiplos critérios e restrições temporais.

### 3.2. Objetivos Específicos

- Modelar a rede de transporte multimodal do Recife, incluindo os diferentes
    modais disponíveis e suas interconexões.
- Coletar e analisar dados sobre o sistema de transporte do Recife, como
    horários de ônibus, frequência do metrô, tempos de viagem em diferentes
    horários e custos associados a cada modal.
- Implementar e adaptar algoritmos clássicos de caminho mais curto, como
    Dijkstra e A*, para o contexto de uma rede multimodal e com custos variados.
- Desenvolver um algoritmo de otimização multiobjetivo que considere diferentes
    critérios, como tempo, custo e impacto ambiental, para a seleção da rota ótima.
- Analisar a complexidade computacional dos algoritmos desenvolvidos e avaliar
    seu desempenho em diferentes cenários.
- Propor uma arquitetura de sistema para uma aplicação de recomendação de
    rotas multimodais baseada nos algoritmos desenvolvidos.

## 4. Metodologia

O projeto será desenvolvido em quatro etapas principais:

**Etapa 1: Revisão da Literatura e Coleta de Dados**

- Revisão sistemática da literatura sobre algoritmos de otimização de rotas
    multimodais, com foco em artigos publicados entre 2019 e 202 4.
- Coleta de dados sobre o sistema de transporte do Recife, utilizando fontes
    como o Grande Recife Consórcio de Transporte, a CTTU (Autarquia de Trânsito
    e Transporte Urbano do Recife) e plataformas de mapas e transporte.

**Etapa 2: Modelagem e Implementação dos Algoritmos**

- Modelagem da rede de transporte do Recife como um grafo multimodal, onde
    os nós representam pontos de parada e interconexão e as arestas representam
    os trechos de deslocamento.
- Implementação dos algoritmos de caminho mais curto (Dijkstra, A*) e do
    algoritmo de otimização multiobjetivo em uma linguagem de programação
    adequada (e.g., Python).

**Etapa 3: Simulação e Análise de Resultados**


- Realização de simulações para avaliar o desempenho dos algoritmos em
    diferentes cenários, considerando variações de horário, dia da semana e
    condições de tráfego.
- Análise comparativa dos resultados obtidos pelos diferentes algoritmos,
    considerando os critérios de otimização definidos.

**Etapa 4: Elaboração do Relatório Final e Proposta de Sistema**

- Elaboração de um relatório técnico detalhando a metodologia, os resultados e
    as conclusões do projeto.
- Proposta de uma arquitetura de sistema para uma aplicação de recomendação
    de rotas multimodais, incluindo a descrição dos componentes e das tecnologias
    a serem utilizadas.

## 5. Cronograma

```
Etapa Mês 1 Mês 2 Mês 3 Mês 4
Revisão da Literatura e Coleta de Dados X X
```
```
Modelagem e Implementação dos Algoritmos X X
```
```
Simulação e Análise de Resultados X X
```
```
Elaboração do Relatório Final e Proposta X
```
## 6. Referências

[1] TomTom Traffic Index. (2023). _Recife Traffic_. Disponível em:
https://www.tomtom.com/traffic-index/recife-traffic/

[2] Bast, H., Delling, D., Goldberg, A., Müller-Hannemann, M., Pajor, T., Sanders,
P., ... & Werneck, R. F. (2016). Route planning in transportation networks. In
_Algorithm engineering_ (pp. 19 - 80). Springer, Cham.

[3] Liu, L., Mu, H., & Yang, J. (2017). Toward algorithms for multi-modal shortest
path problem and their extension in urban transit network. _Journal of Intelligent
Manufacturing_ , 28(5), 1143-1154.

[4] Yusuf, O., Rasheed, A., & Lindseth, F. (2025). Leveraging Big Data and AI for
Sustainable Urban Mobility Solutions. _Urban Science_ , 9(8), 301.

[5] Jain, Y., & Pandey, K. (2025). Transforming Urban Mobility: A Systematic Review
of AI-Based Traffic Optimization Techniques. _Archives of Computational Methods in
Engineering_.

[6] Tu, Q., Cheng, L., Yuan, T., Cheng, Y., & Li, M. (2020). The constrained reliable
shortest path problem for electric vehicles in the urban transportation network.
_Journal of Cleaner Production_ , 257, 120531.


[7] Sharieh, A. (2024). Modeling Metaheuristic Algorithms to Optimal Pathfinding for
Vehicles. _WSEAS Transactions on Computers_ , 23, a605105-029.

[8] Deng, X., Chang, L., Zeng, S., Cai, L., & Poor, H. V. (2022). Distance-based back-
pressure routing for load-balancing LEO satellite networks. _IEEE Transactions on
Wireless Communications_ , 21(11), 9679-9692.

[9] Gendreau, M., Ghiani, G., & Guerriero, E. (2015). Time-dependent routing
problems: A review. _Computers & Operations Research_ , 64, 189-200.

[10] Fang, Z., Li, L., Li, B., Zhu, J., & Li, Q. (2017). An artificial bee colony-based
multi-objective route planning algorithm for use in pedestrian navigation at night.
_International Journal of Geographical Information Science_ , 31(11), 2249-2270.


