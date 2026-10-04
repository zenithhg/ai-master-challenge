# Prompt para Claude Code (VS Code) — Implementar FATOR_CARGA no Clima Deal

Cole este prompt completo no Claude Code, dentro da pasta `submissions/hugo-oliveira/solution/`.

---

## Contexto

Projeto: Lead Scorer com Clima do Deal (G4 AI Master, Challenge 003).

O Clima Deal (`lead_scorer/clima.py`) hoje calcula `CHANCE_BASE(idade)` via tábua de sobrevivência com riscos concorrentes (função `curva_corrigida`). É o único sinal validado no autoteste oficial (`lead_scorer/validacao.py`, função `autoteste`).

Acabamos de testar um novo candidato — **carga de pipeline do vendedor** (quantos deals ele tem abertos simultaneamente) — com o mesmo rigor do autoteste (split cronológico, treino antes do corte, teste depois, sem vazamento). Resultado: **+15,7 pontos** de diferença entre baixa carga e alta carga, confirmado em 3 janelas temporais diferentes (+7,0 / +13,8 / +6,9 pontos). É o segundo sinal real encontrado, atrás só de idade.

Hipótese de negócio: vendedor sobrecarregado (muitos deals abertos ao mesmo tempo) dedica menos atenção a cada um e fecha menos. **Risco conhecido:** pode ser causalidade reversa (vendedor bom fecha rápido → esvazia a carteira → aparece com "baixa carga" sem ser a causa). Documentar essa limitação no README, não escondê-la.

## O que implementar

Adicionar `FATOR_CARGA` como segundo fator multiplicativo:

```
CHANCE_FINAL = CHANCE_BASE(idade) × FATOR_CARGA(carga_atual_do_vendedor)
```

### Passo 1: Função de carga de pipeline (`lead_scorer/clima.py`)

Para um deal, "carga" = quantos deals esse MESMO vendedor tem abertos na MESMA data de referência (incluindo o próprio deal, se ele estiver aberto nessa data).

```python
def carga_pipeline(deals: pd.DataFrame, data) -> pd.Series:
    """Quantos deals o vendedor tem abertos na data, por linha de `deals`.

    Usa só informação disponível na própria data (sem olhar o futuro):
    conta deals do mesmo sales_agent, engajados até `data` e sem desfecho até `data`.
    """
    data = pd.Timestamp(data)
    aberto_na_data = abertos_em(deals, data)
    contagem_por_vendedor = deals.loc[aberto_na_data].groupby("sales_agent").size()
    return deals["sales_agent"].map(contagem_por_vendedor).fillna(0)
```

### Passo 2: Fator de carga por tercil, aprendido com o histórico

Igual à lógica de `curva_corrigida`: só aprende com o que já tinha acontecido até a data de corte (nunca olha o futuro).

```python
def fator_carga(deals: pd.DataFrame, data_corte) -> dict:
    """Fator multiplicativo por faixa de carga (baixa/média/alta), aprendido com
    deals FECHADOS antes de data_corte. Retorna {faixa: fator}.

    Fator = win_rate_da_faixa / win_rate_geral. Faixa sem dado suficiente = 1.0 (neutro).
    """
    data_corte = pd.Timestamp(data_corte)
    fechados = deals[deals["close_date"].notna() & (deals["close_date"] < data_corte)].copy()

    # Carga de cada deal fechado, calculada NO MOMENTO DO ENGAGE dele (não na data_corte)
    cargas = []
    for _, row in fechados.iterrows():
        cargas.append(carga_pipeline(deals, row["engage_date"]).loc[row.name])
    fechados["carga"] = cargas

    if len(fechados) < 200:  # proteção: sem dado suficiente, tudo neutro
        return {"baixa": 1.0, "media": 1.0, "alta": 1.0}

    fechados["faixa"] = pd.qcut(fechados["carga"].rank(method="first"), 3,
                                  labels=["baixa", "media", "alta"])
    win_rate_geral = fechados["ganhou"].mean()
    taxa_por_faixa = fechados.groupby("faixa")["ganhou"].mean()
    return {faixa: (taxa / win_rate_geral if win_rate_geral > 0 else 1.0)
            for faixa, taxa in taxa_por_faixa.items()}
```

**Atenção de performance:** o loop linha a linha acima é didático, não para produção — 8.800 deals vai ficar lento. Vetorizar: para cada deal fechado, a carga no momento do engage pode ser calculada com `groupby` + ordenação por data em vez de loop. Peça ao Claude Code para otimizar isso (é o tipo de problema que ele resolve bem).

### Passo 3: Integrar em `aplicar()`

Na função `aplicar()` existente, depois de calcular `chance` (CHANCE_BASE), multiplicar pelo fator de carga:

```python
# Dentro de aplicar(), após calcular abertos["chance"]:
fatores = fator_carga(base.deals, data)
abertos["carga_atual"] = carga_pipeline(base.deals, data).loc[abertos.index]
abertos["faixa_carga"] = pd.qcut(abertos["carga_atual"].rank(method="first"), 3,
                                   labels=["baixa", "media", "alta"])
abertos["fator_carga"] = abertos["faixa_carga"].map(fatores).fillna(1.0)
abertos["chance"] = (abertos["chance"] * abertos["fator_carga"]).clip(config.PISO_CHANCE, 0.95)
```

### Passo 4: Config

Adicionar em `config.py`:
```python
# Fator de carga de pipeline: fecha menos quem está sobrecarregado.
# Validado no autoteste: +15,7 pontos (3 janelas: +7,0/+13,8/+6,9). Risco conhecido:
# pode ser causalidade reversa (vendedor bom fecha rápido → baixa carga é efeito, não causa).
MIN_CASOS_FATOR_CARGA = 200
TETO_CHANCE = 0.95
```

## Regras obrigatórias (não negociar)

1. **Edição pontual.** Não reescrever `clima.py` inteiro — só adicionar as duas funções novas e os 4 blocos de código em `aplicar()`. Preservar tudo que já existe (`curva_corrigida`, `curva_prd`, estados, etc.)
2. **Sem vazamento temporal.** `fator_carga()` só pode usar deals FECHADOS antes de `data_corte`. Nunca usar `close_date` de um deal ainda aberto na data de referência.
3. **Testar antes de considerar pronto:**
   - Rodar `pytest tests/test_clima.py` — não pode quebrar nada existente
   - Rodar `python -m lead_scorer.validacao` e comparar a nova receita com Clima vs a receita atual (vai aparecer na tabela `sim.resumo` com `vs_feeling` e `vs_maior_valor`) — ESPERADO: melhora sobre o Clima atual, porque adicionar um sinal real não pode piorar o ranking
   - Adicionar uma estratégia nova em `ESTRATEGIAS` dentro de `validacao.py` (`"clima_v2": "Com Clima + Carga"`) para comparar lado a lado com o Clima atual na mesma simulação das segundas, sem apagar a comparação anterior
4. **Não mexer no Score nem no app.py** nesta tarefa — só o Clima Deal.

## Entregável desta tarefa

- `clima.py` com as 2 funções novas + integração em `aplicar()`
- `config.py` com os 2 parâmetros novos
- Testes passando
- Print da simulação (`sim.resumo`) mostrando Clima v1 vs Clima v2 (com carga), para eu avaliar o ganho real antes de fechar o PR

