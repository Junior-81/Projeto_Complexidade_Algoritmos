# Análise das Questões e Alinhamento com o Projeto

## Contexto analisado
Foram considerados:
- o documento da atividade em PDF ([documentation/documento-atvd-complexidade.pdf](documentation/documento-atvd-complexidade.pdf));
- a implementação atual do projeto de rotas multimodais;
- a documentação técnica existente no repositório.

## 1. Análise das questões e possíveis inconsistências

### 1.1 Consistência conceitual das questões do PDF
As questões do PDF estão corretas para introduzir:
- definição de entrada e saída;
- busca linear, busca binária e estrutura hash (set/HashSet);
- noções de complexidade assintótica para diferentes cenários de consulta.

### 1.2 Pontos que podem gerar inconsistência na interpretação
1. Busca binária com ordenação dentro de cada consulta.
- Risco: o aluno pode entender que sempre terá ganho mesmo ordenando toda vez.
- Ajuste recomendado: explicar que o ganho aparece quando a ordenação é feita uma vez e reutilizada em várias consultas.

2. Hash tratado como O(1) absoluto.
- Risco: simplificação excessiva.
- Ajuste recomendado: explicitar que O(1) é custo médio; pior caso pode degradar.

3. Comparação de cenários sem separar pré-processamento de consulta.
- Risco: escolha inadequada do algoritmo no mundo real.
- Ajuste recomendado: mostrar custo total como:
  - preparo dos dados + custo por consulta × número de consultas.

## 2. Inconsistências encontradas entre documentação e código do projeto

1. Garantia de otimalidade do A* descrita de forma forte na documentação.
- Evidência no código: [routing/astar_multimodal.py](routing/astar_multimodal.py#L119) aplica escala na heurística e usa fechamento de estados em [routing/astar_multimodal.py](routing/astar_multimodal.py#L270).
- Risco: em certas condições, pode não manter a propriedade teórica esperada de otimalidade.
- Solução: revisar admissibilidade/consistência da heurística e política de reabertura de estados.

2. Cache com benefício parcial.
- Evidência: há cache multimodal, porém ainda existe recarga de base em [main.py](main.py#L159) mesmo com cache carregado em [main.py](main.py#L155).
- Risco: latência maior que o necessário em execuções repetidas.
- Solução: persistir e reutilizar também a base OSM processada no fluxo principal.

3. Contrato de saída desatualizado em documento funcional.
- Evidência: o texto cita chave rota, mas a implementação retorna edges, segments, resumo em [routing/path_reconstructor.py](routing/path_reconstructor.py#L236).
- Risco: confusão entre consumidor da API e documentação.
- Solução: atualizar documentação e, se necessário, manter alias temporário por compatibilidade.

4. Estado do algoritmo descrito com menos campos do que no código.
- Evidência: docs antigos citam (node, modal), enquanto implementação usa flag adicional usada em restrições.
- Risco: análise de complexidade incompleta.
- Solução: padronizar documentação para refletir o estado real usado pelos algoritmos.

## 3. Soluções recomendadas (objetivas)

1. Correção metodológica da documentação
- Atualizar arquivos de arquitetura/funcionamento para refletir:
  - seleção entre Dijkstra e A*;
  - formato real do estado de busca;
  - contrato real do output.

2. Correção técnica de desempenho
- Integrar cache de base OSM no fluxo principal.
- Avaliar paralelização dos cenários de opções para reduzir tempo de resposta.

3. Correção técnica de qualidade algorítmica
- Ajustar heurística do A* para preservar propriedades desejadas.
- Incluir testes comparativos Dijkstra x A* para validar qualidade da rota e tempo.

4. Correção de rastreabilidade
- Manter um único documento de status real (fonte de verdade) para evitar deriva entre código e documentação.

## 4. Alinhamento de característica técnica das questões com o projeto

### Característica escolhida
Pré-processamento para acelerar múltiplas consultas (analogia direta com a ideia de HashSet/set do PDF).

### Justificativa da escolha
No PDF, a principal mensagem é: quando há muitas consultas, compensa preparar estrutura de dados antes.
No projeto, existe exatamente o mesmo padrão de necessidade:
- endpoint de opções calcula múltiplos cenários;
- construir/normalizar estruturas pesadas repetidamente custa caro;
- cache e indexação tornam consultas subsequentes muito mais rápidas.

### Como alinhar no projeto (prático)
1. Cache de estruturas pesadas (já iniciado) com reutilização completa no fluxo.
2. Indexação para operações repetitivas (ex.: nearest-node).
3. Reuso de resultados por assinatura de entrada (origem, destino, restrição, algoritmo e janela climática).

Conclusão: o alinhamento é tecnicamente coerente e fortalece tanto a eficiência quanto a argumentação de complexidade do projeto.

## 5. Conclusão geral
As questões do PDF estão adequadas para base didática e podem ser alinhadas ao projeto com boa justificativa técnica. As principais inconsistências hoje estão menos nas ideias de complexidade e mais na sincronização entre documentação e implementação. Com as correções propostas, o projeto ganha clareza, consistência e melhor desempenho operacional.