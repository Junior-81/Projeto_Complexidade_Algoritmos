# Atividade de Refinamento de Projetos em Analise e Complexidade de Algoritmos

## 1. Projeto preliminar, problema principal e modelo abstrato
O projeto desenvolvido e um sistema de recomendacao de rotas multimodais (walk, bike, car, moto, bus, uber_car, uber_moto) para calcular caminhos entre origem e destino balanceando tempo, custo e risco. Ele modela a cidade como um grafo multimodal, onde cada aresta representa um deslocamento possivel com atributos de distancia, velocidade, custo e risco, e aplica algoritmos de caminho minimo (Dijkstra ou A*).

O problema computacional principal e: dado um grafo ponderado multimodal e restricoes de transicao modal, encontrar uma rota de menor custo acumulado segundo uma funcao objetivo multiatributo.

Esse problema deve ser analisado em modelo abstrato (ex.: RAM e teoria de grafos) porque:
- a estrutura algoritmica (estados, relaxacoes, fronteira de busca) independe do hardware especifico;
- a classificacao assintotica permite prever escalabilidade para grafos maiores;
- comparacoes entre Dijkstra e A* ficam mais rigorosas quando isolamos fatores acidentais da maquina (cache, SO, rede, etc.).


## 2. Operacoes no modelo RAM: custo constante x custo nao constante
No modelo RAM, no contexto deste projeto:

Operacoes tratadas como custo constante (aproximacao):
- acessos a campos escalares de aresta/no (ex.: distance_km, modal);
- operacoes aritmeticas elementares (+, *, /, comparacoes);
- leituras/escritas em dict e set do Python em caso medio (hash), como g_score[state] e state in closed_set;
- normalizacao pontual de uma metrica com min-max.

Operacoes que exigem tratamento mais cuidadoso:
- operacoes de heap (heapq.heappush/heappop): custo $O(\log n)$;
- iteracao de vizinhos e arestas no grafo: depende do grau dos nos, custo agregado proporcional a $|E|$ no pior caso;
- construcao do grafo multimodal (replicacao por modais e integracao GTFS): cresce com tamanho da malha e dados de transporte;
- carregamento de CSVs, consulta a API de clima e serializacao de cache: custo de I/O e rede, fora da abstracao RAM simples.

Justificativa: na analise de algoritmos, consideramos constante apenas operacoes primitivas locais; toda operacao que depende de estrutura dinamica, tamanho de entrada, rede ou disco deve ser separada para nao mascarar o custo dominante.

## 3. Ambiente real x modelo abstrato: diferencas de custo
Duas (ou mais) diferencas relevantes entre custo teorico e custo pratico observadas no projeto:

1. I/O e rede nao aparecem no custo assintotico da busca, mas pesam no tempo real.
- Teoria: analise de Dijkstra/A* foca em $|V|$, $|E|$, fila de prioridade e relaxacoes.
- Pratica: leitura de varios CSVs, chamada da API Open-Meteo e carregamento/salvamento de cache podem dominar a latencia total em execucoes curtas.

2. Acesso a memoria e overhead de runtime mudam desempenho sem alterar classe assintotica.
- Teoria: acesso a estrutura e considerado custo uniforme.
- Pratica: objetos Python tem overhead alto, localidade de cache de CPU importa, e operacoes em NetworkX/Pandas tem custos constantes maiores que uma implementacao de baixo nivel.

3. Bibliotecas e implementacoes internas alteram constantes.
- Teoria: duas implementacoes de mesmo algoritmo podem ser "equivalentes" em $O$.
- Pratica: funcoes vetorizadas (NumPy/Pandas) e trechos em C podem ser muito mais rapidos que loops puros em Python.

4. Concorrencia/assincronismo (quase ausente no fluxo principal) tambem distancia teoria de pratica.
- Teoria classica costuma assumir execucao sequencial.
- Em ambiente real, latencias de rede poderiam ser escondidas por paralelismo/async, mudando tempo de parede sem mudar o limite assintotico da busca.

## 4. Algoritmo central e funcao de custo assintotica
Algoritmo central escolhido: Dijkstra multimodal (tambem ha A*).

Definicoes:
- $V_s$: numero de estados de busca. No projeto, estado e $(no, modal, used_bus)$, entao $V_s$ e proporcional a $|V| \cdot |M| \cdot 2$.
- $E_s$: numero de transicoes entre estados (arestas multimodais validas).

Pseudocusto do Dijkstra com heap binaria:
- cada extracao da fila custa $O(\log V_s)$;
- cada relaxacao bem-sucedida gera insercao na fila, tambem $O(\log V_s)$;
- custo total aproximado:

$$
T(|V_s|, |E_s|) \approx c_1 |V_s|\log|V_s| + c_2 |E_s|\log|V_s|
$$

Classificacao assintotica:
- limite superior: $O((|V_s| + |E_s|)\log|V_s|)$;
- limite inferior (com necessidade de explorar componentes relevantes): $\Omega(|V_s|)$;
- em grafos esparsos e conectados com heap: comportamento tipico $\Theta((|V_s| + |E_s|)\log|V_s|)$.

Para A*, a ordem de pior caso permanece da mesma familia, embora na pratica normalmente expanda menos estados por causa da heuristica.

## 5. Trechos com laco simples e lacos aninhados
Exemplo de laco simples (crescimento linear):
- etapa de normalizacao no fluxo principal registra tempo/custo/risco percorrendo arestas do grafo.
- custo: $O(E)$, com limite operacional por amostragem (no codigo atual, teto de 80.000 arestas), o que na pratica vira $O(\min(E, 80000))$.

Exemplo de lacos aninhados/chamadas repetidas (crescimento maior):
- na busca (Dijkstra/A*), ha:
  - laco principal sobre estados removidos da fila;
  - para cada estado, iteracao sobre vizinhos;
  - para cada vizinho, iteracao sobre arestas paralelas (modais).
- isso equivale ao processamento de transicoes do grafo de estados e resulta em custo agregado de relaxacoes proporcional a $E_s$, com fator logaritmico da heap.

Impacto no crescimento:
- lacos simples tendem a escalar linearmente com o tamanho da colecao percorrida;
- lacos aninhados na busca, somados a operacoes de heap, levam ao crescimento quase-linear multiplicado por $\log V_s$, que se torna o gargalo principal em grafos grandes.

No nosso projetos temos dois pontos principais de laços simples e aninhados. Laço simples pode ser visto no trecho de normalização dos dados onde ocorre a iteração e registro em cada aresta, já laços aninhados são utilizados na navegação entre estados (quando falo em estado é o que representaria o nó porem com mais informações como modal utilizado, se já utilizou onibus na locomoção anterior, etc). No nosso caso o laço simples aumenta de forma linear de acordo com a quantidade de variaveis ou arestas no projeto, já no laço aninhado ele percorre estados vizinhos e para cado estado vizinho é analisado as areastas e modais possiveis aumentando o tempo de processamento conforme quantidade de vizinhos, de modais e outras variaveis analisadas.

## 6. Recursao ou formulacao iterativa
Nao ha recursao relevante nos algoritmos centrais do projeto. A busca e implementada de forma iterativa com:
- fila de prioridade (heap);
- conjuntos de aberto/fechado;
- mapa de predecessores para reconstrucao do caminho.

Por que a formulacao iterativa foi suficiente (e preferivel):
- algoritmos classicos de caminho minimo em grafos (Dijkstra/A*) sao naturalmente iterativos;
- evita limites de profundidade de recursao do Python em rotas longas;
- facilita controle de parada, metricas de iteracao e restricoes de modal;
- melhora previsibilidade de memoria em comparacao com pilha de chamadas recursivas.

Em resumo, para este tipo de problema em grafos urbanos grandes, a abordagem iterativa e a escolha tecnica mais adequada.
