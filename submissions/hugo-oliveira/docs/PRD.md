# PRD: Lead Scorer com Clima do Deal (v1)

> Desenho aprovado por Hugo em 01/10/2026: **Score + Clima do Deal + Raio X do Cliente**. Entrega: PR do case 003 até 06/10/2026.
>
> **Revisão de 02/10/2026:** curva do Clima corrigida, estados novos, selo "esfriando" e impacto refeito pela simulação das segundas (seções 5.2, 5.4, 9 e 10).

## 1. Problema

A Head de Revenue Operations: *"Nossos vendedores gastam tempo demais em deals que não vão fechar e deixam oportunidades boas esfriar."* São 35 vendedores, cerca de 8.800 oportunidades, e a priorização é feita no feeling.

O que os dados mostram:
- 2.089 negociações abertas, somando $4,97 milhões a preço de tabela (cerca de 5 meses de receita).
- 1.291 delas (81% das que estão em negociação, $3,2 milhões) estão paradas há mais tempo que qualquer venda que já fechou (138 dias).
- 68% das abertas não têm conta cadastrada.
- Perfil do cliente (setor, porte, sede) não prevê ganho. O sinal que se sustenta é o **tempo**: depois de 90 dias aberto, o deal esfria, e 7 em cada 10 nunca fecham.

## 2. Objetivo e critérios de sucesso

| Critério | Meta | Como medir |
|---|---|---|
| Vendedor responde "onde foco hoje?" | Menos de 60 segundos | Teste com o Hugo |
| Acerto do foco | Mais semanas em deal que termina ganho (48% contra 43% no feeling) e menos tempo em deal que nunca fecha (31% contra 36%) | Simulação das segundas na tela Validação |
| Roda seguindo o README | Do zero em menos de 5 minutos | Teste em clone limpo |
| Explicação | Todo número com o porquê em frase de vendedor | Revisão do Hugo |

## 3. Usuários

- **Vendedor:** abre na segunda de manhã. Quer saber onde focar, por quê e o que falar.
- **Gerente:** quer ver a carteira do time, quem tem pipeline parado e onde intervir.
- **RevOps:** quer confiar no método (validação e autoteste).

## 4. Jornada do vendedor (v1)

1. Abre o app e escolhe o próprio nome (ou gerente, ou região).
2. Vê a semana dele: foco, qualificar, nutrir, sem cadastro, valor em jogo e a própria conversão.
3. Lista **Hoje**: deals "Atacar agora" e "Fechar rápido", ordenados pelo Score.
4. Abre um deal: aba **Raio X** com a ficha do cliente, o Clima, o porquê, o produto do porte e a matemática do 1%.
5. Faz a consulta médica: seleciona dores, tempo da dor e o que o cliente já testou. Recebe a contraobjeção e o script de abordagem.
6. Fecha (Win ou Lost): responde 5 perguntas. A resposta vira o case do mês e alimenta o autoteste.

## 5. Regras de negócio

### 5.1 Preparação dos dados
- **Data de referência:** última data do dataset (31/12/2017), configurável. Nunca a data de hoje: com ela, todo deal pareceria parado há quase 9 anos.
- Corrigir `GTXPro` para `GTX Pro` (1.480 deals) e `technolgy` para `technology`.
- Deal sem conta: marcar "sem cadastro" (1.425 abertos).
- Valor de deal aberto = preço de tabela do produto (`close_value` só existe nos fechados).

### 5.2 Clima do Deal (chance de fechar)
- **Idade** = dias desde o engage até a data de referência.
- **Chance** = probabilidade de um deal aberto com essa idade terminar ganho. A curva aprende com todos os deals da história, inclusive os que continuam abertos e talvez nunca fechem (método: tábua de sobrevivência que separa ganho e perda).
- **Correção de 02/10:** a versão 1 aprendia só com deals fechados e dizia que deal velho era o melhor (76% aos 120 dias). A simulação das segundas mostrou o contrário: de 91 a 138 dias, só 21% ganharam e 69% nunca fecharam. Só pela chance, a versão 1 perdia para o sorteio. A curva corrigida acompanha a realidade (nota de ordenação 0,65 contra 0,53; 0,5 é cara ou coroa).

| Deal aberto há | Chance de terminar ganho | Deals que chegaram a essa idade |
|---|---|---|
| 0 dias | 52% | 8.300 |
| 14 dias | 50% | 5.580 |
| 30 dias | 49% | 5.128 |
| 60 dias | 46% | 4.549 |
| 90 dias | 35% | 2.895 |
| 100 dias | 27% | 2.353 |
| 110 dias | 18% | 1.905 |
| 120 dias | 9,5% | 1.595 |
| 130 dias ou mais | piso de 5% | 1.393 |

- **Estados:**
  - **Novo** (0 a 14 dias): hora de qualificar (consulta médica).
  - **Ativo** (15 a 90 dias): chance estável, perto de 50%.
  - **Esfriando** (91 a 138 dias): a chance cai rápido. O deal ganha o selo "esfriando: última tentativa esta semana".
  - **Sem precedente** (mais de 138 dias): nenhuma venda da história fechou depois disso.
  - **A qualificar** (Prospecting): ainda sem data de engage.
- **Premissas explícitas (configuráveis em `config.py`):**
  - Piso de 5% no fim da curva e para deal sem precedente. A pesquisa Win/Lost vai medir a taxa real de recuperação e substituir o piso.
  - Prospecting: usa a chance do dia 0 (52%) como "chance se engajar".
- **Autoteste dos outros indicadores** (aprende com o que fechou antes de 01/07/2017; testa nos deals que engajaram de 01/07 a 14/08/2017):
  - Desligados: setor, porte, funcionários, sede, faz parte de grupo, histórico da conta, histórico do vendedor e relacionamento (que inverte: 9 pontos a menos no teste).
  - Em observação: idade da conta (+2,7 pontos).
  - Região e gerente: ligados (+16 e +10 pontos), mas não entram no Score. Todos os deals de um vendedor têm a mesma região e o mesmo gerente, então não mudam a ordem da lista dele. E o efeito vem de deals que nunca fecham: na Central, 52% dos deals de julho e agosto nunca fecharam, contra 19% a 23% nas outras regiões. Vão para a visão do gerente.
- **Sem conta não vira sinal:** na base, só deal aberto fica sem conta. Usar isso para prever seria olhar o futuro.

### 5.3 Score (0 a 100)
- **Valor esperado** = chance x preço de tabela.
- **Score** = posição percentual do valor esperado entre todos os deals abertos do time. Score 90 = valor esperado maior que o de 90% do pipeline.
- Frase para o vendedor (exemplo): *"Deals como este, abertos há 45 dias, terminaram ganhos 48% das vezes. Vale $4.821. Valor esperado: $2.309."*

### 5.4 Rótulos de ação (próxima melhor ação)
Valor alto = produto de $3.393 ou mais (MG Advanced, GTX Pro, GTX Plus Pro, GTK 500).

| Situação | Rótulo | Abertos | Valor | O que fazer |
|---|---|---|---|---|
| Ativo ou esfriando + valor alto | Atacar agora | 120 | $583 mil | Consulta médica e proposta |
| Ativo ou esfriando + valor baixo | Fechar rápido | 171 | $94 mil | Fechar com esforço mínimo |
| Prospecting ou novo | Qualificar em 14 dias | 507 | $1,09 milhão | Consulta médica em até 14 dias |
| Sem precedente + com conta + valor alto | Nutrição de elite | 180 | $935 mil | Régua de 90 dias com o vendedor |
| Sem precedente + com conta + valor baixo | Limpar ou automação | 232 | $130 mil | Régua automática ou fechar como Lost |
| Sem precedente + sem conta | Completar cadastro ou limpar | 879 | $2,13 milhões | Completar cadastro em 7 dias ou fechar |

- Selo **Sem cadastro** em qualquer deal sem conta (204 dos 291 deals ativos ou esfriando).
- Selo **Esfriando** em deal de 91 a 138 dias: "última tentativa esta semana". Hoje são 188: 83 dos 120 "Atacar agora" e 105 dos 171 "Fechar rápido".
- Vendedor mediano: 4 "Atacar agora", 3 "Fechar rápido", 7 "Nutrição de elite", 9 "Limpar ou automação" e 32 "Completar cadastro ou limpar".

### 5.5 Raio X do Cliente (aba do deal)
- **Ficha no estilo scout de futebol:** negociações, vitórias, derrotas, aproveitamento contra a média (63%), últimos 5 resultados (V V D V D), produto mais comprado, ticket médio, dias desde a última compra e vendedores que já atenderam.
- **Produto do porte:** mix de produtos ganhos por faixa de receita da conta, com diferença real (p < 0,001). Conta pequena compra mais MG Special (23% contra 14% na grande); conta grande compra mais MG Advanced (18% contra 13%). Ticket médio: grande $2.541, pequena $2.237. Setor não muda o mix.
- **Matemática do 1% (Alfredo Soares):** preço do produto dividido pelo faturamento anual da conta (`revenue` está em milhões de US$). Máximo da base: 0,12%.
- **Deal sem conta:** ficha vazia, com o aviso "complete o cadastro para ver o Raio X".

### 5.6 Consulta médica e contraobjeção
- **Campos:**
  - Dores: seleção múltipla em lista mapeada (a lista é definida pelo Hugo).
  - Há quanto tempo dói: menos de 3 meses, de 3 a 12 meses, mais de 1 ano.
  - O que já testou: lista.
  - Investigação pré-pitch: como está o negócio, último trimestre, prioridade de investimento, orçamento.
- **Contraobjeção sugerida:** regra "o que já testou" leva ao argumento (tabela editável).
- **Embalagem (Alfredo):** se o cliente já investe na área, a oferta é "otimização"; se não, é "inovação".
- Grava em `solution/data/feedback/consultas.csv`.

### 5.7 Nutrição (régua de 90 dias)
- **Triagem:** sem conta vai para completar cadastro; nutrição de elite fica com o vendedor; limpar ou automação vai para a régua automática.
- **Passos:**
  - Dia 0: conteúdo útil sobre o produto.
  - Dia 15: case do mesmo porte.
  - Dia 30: convite para demo.
  - Dia 60: condição comercial ou produto de entrada do porte.
  - Dia 90: decisão. Volta ao pipeline ou fecha como Lost com motivo.
- **Alerta para o gerente:** deal de valor alto, sem precedente, com 5 tentativas sem resposta: trocar de vendedor (Alfredo).
- A v1 mostra o passo e a data. O envio automático fica para a evolução.

### 5.8 Pesquisa Win/Lost e autoteste
- **5 perguntas obrigatórias ao fechar:** motivo principal, objeção que apareceu, decisor mapeado (sim ou não), concorrente (sim ou não, e qual), origem do lead.
- A resposta vira o **case do mês** (Alfredo) e alimenta o autoteste.
- **Autoteste:** um indicador, existente ou novo, só liga se, no teste temporal (aprende no passado, testa no futuro), separar ganhos de perdas com diferença de 5 pontos ou mais e amostra de 200 ou mais. Fora isso, fica "em observação" ou "desligado". A tela Validação mostra o status.

## 6. Telas da v1
1. **Hoje:** lista do vendedor, com filtros de vendedor, gerente e região.
2. **Raio X do Cliente:** aba ao abrir um deal.
3. **Nutrir:** lista de nutrição e limpeza.
4. **Minha conversão:** painel do vendedor (taxa de ganho, ticket, ciclo e ganhos por mês contra a média do time).
5. **Time:** visão do gerente.
6. **Validação:** como o Clima foi testado e o status do autoteste.

## 7. Fora da v1 (evolução)
- Enriquecimento com os dados que o Alfredo pede: sócios, canal de origem (UTM), engajamento e nível de consciência, consulta médica completa.
- Envio automático da régua de nutrição e acervo dos conteúdos que mais vendem.
- Objeções aprendidas por perfil.
- Integração com CRM e com o G4 OS; alertas por e-mail ou Slack; histórico do score.
- Piloto de 30 dias, com metade do time usando a ferramenta, para medir receita e horas.

## 8. Requisitos não funcionais
- Python 3.10 ou mais recente, Streamlit. Instala com `pip install -r requirements.txt` e roda com `streamlit run app.py`.
- Funciona sem internet e sem chave de API.
- Dados do dataset (licença CC0) incluídos no repositório, conferidos com o download oficial do Kaggle.
- Interface em português, sem jargão. Carrega em menos de 5 segundos (cache).
- Código em módulos, com testes das regras (pytest).
- Só arquivos dentro de `submissions/hugo-oliveira/`.

## 9. Impacto (para o README e o pitch)

**Medido** na simulação das segundas: 16 segundas, de maio a agosto de 2017, 30 vendedores. Toda segunda, cada vendedor escolhe 5 deals abertos para trabalhar na semana (o time fechou 5,1 deals por vendedor por semana). O resultado é conferido até 31/12/2017 e nada do futuro entra na escolha. Cada deal conta uma vez na receita.

| Vendedor médio, 16 semanas | Sem Clima: feeling (sorteio) | Sem Clima: maior valor | Com Clima |
|---|---|---|---|
| Semanas de foco em deal que terminou ganho | 43% | 40% | **48%** |
| Tempo em deal que nunca fechou | 36% | 41% | **31%** |
| Deals trabalhados | 54 | 14 | 23 |
| Receita dos deals trabalhados | $57,3 mil | $39,6 mil | **$60,3 mil** |
| Receita por deal trabalhado | $1.057 | $2.881 | $2.582 |

- **Contra quem persegue o maior valor: +52,5% de receita.** O Clima ganha em 26 de 30 vendedores (ganho mediano de 38%). O maior valor fica preso em deal caro que nunca fecha.
- **Contra o feeling: +5% de receita com menos da metade dos deals.** Cada deal do Clima rende 2,4 vezes mais. O Clima ganha em 19 de 30 vendedores (ganho mediano de 10%).
- **A correção da curva faz a diferença:** com a curva da versão 1, a receita seria $47,5 mil, abaixo do feeling.
- **Produtividade por hora** (premissa: 8 horas por dia útil; é equivalência, não medição): o vendedor médio gerou $191 por hora de março a dezembro de 2017, com sazonalidade de trimestre (junho $254, julho $138). Com o ganho conservador de 5%, vai a $201 por hora. Com as 40 horas da semana divididas entre os 5 deals, o tempo em deal que nunca fecha cai de 14,3 horas (feeling) ou 16,2 horas (maior valor) para 12,3 horas por semana.
- **Dinheiro parado:** $3,2 milhões sem precedente. Cada 5% recuperado vale $160 mil.
- **Produtividade mensurável:** o vendedor mediano tem 79 negociações abertas; o foco dele (Atacar agora + Fechar rápido) tem 12.
- **Retirado:** o "60% para 67%" e o cenário de +$92 mil por mês da versão 1. Valiam só entre deals que fecharam, não na segunda-feira do vendedor.
- A simulação mede a qualidade da lista, não a causa. A prova causal é o piloto (seção 7).

## 10. Limitações
- Base sintética: o perfil não prevê o resultado; só o tempo se sustentou no teste.
- Na base, só deal aberto fica sem conta (1.425): não dá para usar "sem conta" como sinal sem olhar o futuro.
- Em 11 de 30 vendedores, escolher ao acaso teria rendido mais que o Clima na simulação.
- A simulação não mede causa: supõe que dar mais atenção a um deal não muda a chance dele.
- Sem histórico de estágio, sem registro de atividade e sem data prevista de fechamento.
- 68% dos deals abertos estão sem conta: o Raio X fica vazio para eles.
- O corte de 138 dias é do dataset. Num CRM real, a curva deve ser recalculada.
- Premissas explícitas: piso de 5% para "sem precedente" e chance do dia 0 para Prospecting.

## 11. Riscos

| Risco | Mitigação |
|---|---|
| App não roda na máquina do avaliador | Requirements fixos, teste em clone limpo, dados no repositório |
| Parecer com o baseline da IA | Autoteste, validação honesta, playbook do Alfredo, dores do Hugo |
| Escopo | Corte da v1 acima; o resto vai para o README |
| Dados não oficiais | Conferir checksum com o Kaggle antes do commit |

## 12. Pendências
- Hugo: lista de 8 a 10 dores reais, lista do "o que já testou" e as contraobjeções (`docs/playbook.md`).
- Nome do produto. Nome de trabalho: Lead Scorer com Clima do Deal.
- ~~Conferir os dados com o Kaggle oficial. Licença do Xcode e clone do fork.~~ Feito em 01/10.
- Hugo: revisar o rascunho do playbook no Notion (dores, o que já testou, contraobjeções e scripts).
