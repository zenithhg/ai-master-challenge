> **Rascunho histórico, abortado em 03/10/2026.** Este foi o primeiro desenho do Clima do Deal, com 4 fatores além da idade. No autoteste, vendedor, setor e conta inverteram o sinal e a fórmula foi abandonada. Os exemplos com nomes (João, TechCorp) são ilustrativos, não saem dos dados. O algoritmo final, com os números reproduzíveis, está na seção "O algoritmo: Clima do Deal" do [README](../README.md).

# Clima Deal: Documentação do Algoritmo v1

> Desenhado em 02/10/2026. Autor: Hugo Oliveira + Claude.

---

## 1. Conceito

O **Clima Deal** responde uma pergunta simples: *qual a chance real de este deal fechar?*

Assim como a previsão do tempo combina temperatura, umidade, pressão e vento para chegar em "70% de chuva", o Clima Deal combina múltiplos parâmetros contextuais de um deal para calcular uma probabilidade de fechamento.

O **Score** (já existente) rankeia deals por valor esperado: diz *qual atacar primeiro*.
O **Clima** complementa com probabilidade real: diz *qual a chance de fechar*.

Juntos: vendedor sabe onde focar **e** o que esperar de cada deal.

---

## 2. Fórmula Final

```
CHANCE_FINAL = CHANCE_BASE(idade) × FATOR_VENDEDOR × FATOR_SETOR × FATOR_CONTA × FATOR_REGIÃO
```

**Resultado:** número entre 5% e 95% (piso e teto aplicados ao final).

---

## 3. Parâmetros

### 3.1 CHANCE_BASE(idade) — ponto de partida

**O que é:** probabilidade histórica de um deal fechar, dado quantos dias ele está aberto.

**Analogia:** é o "clima base da estação". No inverno, chove mais. No verão, menos. Antes de olhar qualquer fator específico, o tempo em aberto já diz muito.

**Como calcula:** tábua de sobrevivência com riscos concorrentes. Aprende com todos os deals históricos: ganhos, perdas E os que ainda estão abertos (e talvez nunca fechem). Isso corrige o viés de contar só os fechados.

**Fonte de dado:** `sales_pipeline.csv` (engage_date, close_date, deal_stage)

**Referência atual:**

| Idade do deal | CHANCE_BASE |
|---|---|
| 0 dias | 52% |
| 30 dias | 49% |
| 60 dias | 46% |
| 90 dias | 35% |
| 110 dias | 18% |
| 130+ dias | 5% (piso) |

**Nota:** CHANCE_BASE não é um fator multiplicativo. Ela é o ponto de partida sobre o qual os fatores abaixo atuam.

---

### 3.2 FATOR_VENDEDOR

**O que é:** quão melhor (ou pior) este vendedor fecha, comparado com a média do time.

**Fórmula:** `win_rate_vendedor ÷ win_rate_média_geral`

**Exemplos:**
- Vendedor A fecha 55%, média é 50% → fator = 1,10 (10% acima da média)
- Vendedor B fecha 40%, média é 50% → fator = 0,80 (20% abaixo da média)
- Sem histórico suficiente → fator = 1,0 (neutro)

**Fonte de dado:** `sales_pipeline.csv` (sales_agent, deal_stage) + `sales_teams.csv` (sales_agent)

---

### 3.3 FATOR_SETOR

**O que é:** quão melhor (ou pior) deals deste setor convertem.

**Fórmula:** `win_rate_setor ÷ win_rate_média_geral`

**Fonte de dado:** `accounts.csv` (sector) + `sales_pipeline.csv` (account, deal_stage)

---

### 3.4 FATOR_CONTA

**O que é:** histórico de compra desta conta específica com a empresa.

**Fórmula:** `taxa_ganho_conta ÷ taxa_ganho_média_geral`

**Exemplos:**
- Conta que já comprou 3 de 4 vezes → fator alto (cliente recorrente)
- Conta nova, sem histórico → fator = 1,0 (neutro)
- Conta que tentamos 5 vezes e nunca fechou → fator baixo

**Fonte de dado:** `sales_pipeline.csv` (account, deal_stage) — histórico de deals anteriores por conta

---

### 3.5 FATOR_REGIÃO

**O que é:** performance histórica do escritório regional.

**Fórmula:** `win_rate_região ÷ win_rate_média_geral`

**Contexto real do dataset:** a região Central tem desempenho notavelmente pior (52% dos deals de jul/ago nunca fecharam, contra 19-23% nas outras regiões). Esse fator captura isso.

**Fonte de dado:** `sales_teams.csv` (sales_agent, regional_office) + `sales_pipeline.csv`

---

## 4. Proteções

| Situação | Comportamento |
|---|---|
| Parâmetro sem histórico suficiente | Fator = 1,0 (neutro: não penaliza, não bonifica) |
| CHANCE_FINAL calculada > 95% | Teto em 95% (nenhum deal é certeza) |
| CHANCE_FINAL calculada < 5% | Piso em 5% (nenhum deal é impossível) |

**Lógica do neutro:** se não temos dados de um vendedor novo ou de um setor raro, não devemos punir o deal por isso. Mantemos a base histórica do tempo (CHANCE_BASE) e deixamos os fatores com histórico operarem.

---

## 5. Exemplo Numérico

**Deal:** TechCorp, vendedor João, setor Technology, região Central, aberto há 45 dias.

| Parâmetro | Valor | Origem |
|---|---|---|
| CHANCE_BASE(45 dias) | 48% | Tábua de sobrevivência |
| FATOR_VENDEDOR (João: 58% vs 50% média) | 1,16 | sales_pipeline + sales_teams |
| FATOR_SETOR (Technology: 52% vs 50%) | 1,04 | accounts + sales_pipeline |
| FATOR_CONTA (TechCorp: 2 ganhos de 3) | 1,33 | sales_pipeline histórico |
| FATOR_REGIÃO (Central: 44% vs 50%) | 0,88 | sales_teams + sales_pipeline |

**Cálculo:**
```
CHANCE_FINAL = 0,48 × 1,16 × 1,04 × 1,33 × 0,88
CHANCE_FINAL = 0,48 × 1,414
CHANCE_FINAL = 67,9%
```

**Leitura para o vendedor:** *"Deal aberto há 45 dias com TechCorp. Chance de fechar: 68%. João fecha acima da média, a conta tem bom histórico, mas a região Central puxa um pouco para baixo."*

---

## 6. O que NÃO está na v1 (melhorias para v2)

Os parâmetros abaixo foram identificados como relevantes, mas os dados não existem no dataset atual do challenge:

| Parâmetro v2 | Por que seria útil | Dado necessário |
|---|---|---|
| Engajamento em redes sociais | Deals com alto engajamento tendem a fechar mais rápido | Dados de social/CRM |
| NPS / satisfação do cliente | Conta com promotores volta a comprar | Dados de NPS |
| Histórico de suporte | Muitos tickets abertos pode travar a venda | Dados de CS/support |
| Tamanho relativo do deal | Deal pequeno p/ conta grande fecha mais fácil | Revenue da conta vs valor do deal |
| Nível de consciência | Cliente em "Consideration" vs "Awareness" tem chances diferentes | Dados de marketing |

**Ação para v2:** ao integrar com CRM real, esses parâmetros entram como novos fatores multiplicativos. A fórmula escala sem mudar a estrutura.

---

## 7. Relação com o Score

O Clima e o Score são complementares, não concorrentes:

| | Clima Deal | Score |
|---|---|---|
| Pergunta | "Qual a chance de fechar?" | "Qual deal atacar primeiro?" |
| Output | Percentual (%) | Posição percentual (0-100) |
| Base | Probabilidade × fatores contextuais | Valor esperado = chance × preço |
| Uso | Raio X do deal, Clima visual | Ordenação da lista "Hoje" |

O Score usa o Clima como insumo: `valor_esperado = CHANCE_FINAL × preço_de_tabela`.

---

*Próximo passo: implementar em `clima.py` — expandir `aplicar()` para calcular os 4 fatores e multiplicar pela CHANCE_BASE existente.*
