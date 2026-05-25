# Análise das Questões e Alinhamento Técnico (Versão 2)

## Objetivo
Apresentar inconsistências identificadas nas questões e no projeto, com propostas de solução, além de verificar o alinhamento entre características técnicas estudadas e a implementação atual.

## 1. Análise das questões

As questões do PDF estão adequadas para ensino introdutório de análise de algoritmos, especialmente nos pontos:
- definição de entrada e saída;
- comparação entre busca linear, busca binária e estrutura hash;
- escolha de algoritmo por cenário de uso.

### Possíveis inconsistências nas questões
1. Busca binária pode ser interpretada com ordenação em toda consulta.
- Impacto: a vantagem pode desaparecer em cenários com poucas consultas.
- Solução: deixar explícito que a ordenação deve ser feita uma vez e reaproveitada.

2. Hash pode ser entendido como sempre O(1).
- Impacto: simplificação técnica incorreta.
- Solução: indicar que O(1) é custo médio, não garantia absoluta para todo caso.

3. Comparação de cenários sem separar preparo e consulta.
- Impacto: decisão de algoritmo pode ficar equivocada.
- Solução: comparar custo total como preparo + consultas.

## 2. Inconsistências do PDF

1. A busca binária pode ser interpretada de forma incompleta.
- O PDF mostra a ordenação como parte da solução, mas pode dar margem à leitura de que ordenar a cada consulta é aceitável sem custo relevante.
- Isso pode ocultar o fato de que a ordenação tem custo e só compensa quando há reutilização da lista ordenada.

2. A estrutura hash aparece como solução sempre O(1).
- O material apresenta a consulta em hash como tempo constante, mas não reforça que isso é uma média esperada, não uma garantia absoluta.
- Em uma análise mais rigorosa, seria importante destacar o custo médio e o pior caso.

3. A comparação entre algoritmos simplifica demais o cenário.
- O PDF compara busca linear, binária e hash em um problema de consulta em lista.
- Embora didático, o texto pode passar a impressão de que basta olhar para a busca isoladamente, sem considerar o custo de preparo dos dados.

## 3. Soluções para as inconsistências do PDF

1. Explicitar o custo de preparação da busca binária.
- Informar que a ordenação precisa ser feita uma vez para valer a pena em múltiplas consultas.
- Isso reforça a diferença entre custo inicial e custo de consulta.

2. Corrigir a formulação da complexidade da hash.
- Indicar que o custo de consulta é O(1) em média.
- Se necessário, mencionar que a estrutura pode degradar em cenários adversos, embora isso não seja o foco da atividade.

3. Apresentar a comparação de forma mais completa.
- Mostrar que o melhor algoritmo depende não só da consulta em si, mas também do custo de preparo e do número de vezes que os dados serão reutilizados.
- Isso melhora a coerência da análise sem perder a simplicidade didática.

## 4. Alinhamento com o projeto atual

O projeto se alinha ao conteúdo do PDF principalmente na ideia de preparar estruturas antes de consultar várias vezes.

Enquanto o PDF trabalha com uma lista de matrículas e compara linear, binária e hash, o projeto aplica o mesmo princípio em um problema mais amplo, usando:
- cache de estruturas pesadas;
- normalização prévia de métricas;
- reuso de informações já processadas para acelerar novas execuções.

Esse alinhamento é justificável porque, nos dois casos, a pergunta central é a mesma: vale mais a pena consultar diretamente ou investir em preparo para tornar consultas futuras mais eficientes?

### Característica escolhida
Pré-processamento para acelerar múltiplas consultas (mesma lógica conceitual do uso de set/HashSet no PDF).

### Justificativa
O projeto executa cenários repetidos e operações pesadas. Assim como nas questões, preparar estruturas antes das consultas reduz custo total e melhora escalabilidade.

### Aplicação prática no projeto
- cache de estruturas de grafo;
- indexação para operações de busca recorrentes;
- reuso de resultado por assinatura de entrada.

## Conclusão geral
A análise mostra que as questões estão corretas como base conceitual e se alinham ao projeto, principalmente no princípio de preparar dados para muitas consultas. As principais inconsistências estão na sincronização entre documentação e implementação, com soluções técnicas objetivas e de baixo risco para evolução.