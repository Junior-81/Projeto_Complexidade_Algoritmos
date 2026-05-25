## 1.
O projeto desenvolvido e um sistema de recomendacao de rotas multimodais (walk, bike, car, moto, bus, uber_car, uber_moto) para calcular caminhos entre origem e destino balanceando tempo, custo e risco. Ele modela a cidade como um grafo multimodal, onde cada aresta representa um deslocamento possivel com atributos de distancia, velocidade, custo e risco, e aplica algoritmos de caminho minimo (Dijkstra ou A*).

Pode ser analisado por modelo abstrado pois a estrutura de algoritmo montada indepede de hardware especifico para execução e a comparação entre Dijkstra e A* fica melhor quando se isola fatores da maquina como cache, SO, memoria ou rede.

## 5. Trechos com laco simples e lacos aninhados
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
