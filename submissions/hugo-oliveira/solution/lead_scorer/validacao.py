"""Validação do Clima do Deal.

- Simulação das segundas: em 16 segundas (maio a agosto de 2017), cada
  vendedor escolhe 5 deals abertos para trabalhar na semana. Comparamos quatro
  jeitos de escolher e conferimos o que aconteceu com esses deals até 31/12/2017.
- Nota de ordenação e calibração: a chance prevista bate com a realidade?
- Autoteste: outros indicadores só entram se provarem valor no teste temporal.
- Produtividade: receita por vendedor e por hora, mês a mês.

Regra de ouro: nada do futuro entra na escolha. Em cada segunda, a curva só
aprende com o que já tinha acontecido até aquele dia.

Para ver os números: `python -m lead_scorer.validacao` (dentro de solution/).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

import config
from lead_scorer import clima

ESTRATEGIAS = {
    "clima": "Com Clima",
    "clima_prd": "Clima com a curva do PRD (versão 1)",
    "maior_valor": "Sem Clima: maior valor",
    "sorteio": "Sem Clima: feeling (sorteio)",
}

INDICADORES = (
    "setor", "porte", "funcionarios", "idade_da_conta", "faz_parte_de_grupo", "sede",
    "regiao", "gerente", "historico_do_vendedor", "historico_da_conta", "relacionamento",
)
# Iguais para todos os deals de um mesmo vendedor: não mudam a ordem da lista
# dele. Se ligarem, servem à visão do gerente, não ao Score do deal.
IGUAIS_NO_VENDEDOR = ("regiao", "gerente", "historico_do_vendedor")

FAIXAS_IDADE = [-1, 14, 30, 60, 90, 138, 100_000]
ROTULOS_FAIXA = ["0-14", "15-30", "31-60", "61-90", "91-138", "139+"]


# ---------------------------------------------------------------------------
# Simulação das segundas
# ---------------------------------------------------------------------------
@dataclass
class Simulacao:
    segundas: pd.DatetimeIndex
    vendedores: list
    retratos: pd.DataFrame            # deals abertos em cada segunda, com a chance das duas curvas
    por_vendedor: pd.DataFrame        # estratégia x vendedor
    resumo: pd.DataFrame              # time inteiro, por estratégia
    vendedor_a_vendedor: pd.DataFrame  # em quantos vendedores o Clima ganha
    acumulado: pd.DataFrame           # receita acumulada do vendedor médio, por segunda


def retratos_das_segundas(base, segundas) -> pd.DataFrame:
    """Deals abertos em cada segunda, com a chance calculada só com o passado."""
    colunas = ["opportunity_id", "sales_agent", "sales_price", "engage_date", "close_date", "ganhou"]
    partes = []
    for segunda in segundas:
        corrigida = clima.curva_corrigida(base.deals, segunda)
        prd = clima.curva_prd(base.deals, segunda)
        r = base.deals.loc[clima.abertos_em(base.deals, segunda), colunas].copy()
        r["segunda"] = segunda
        r["idade"] = (segunda - r["engage_date"]).dt.days
        r["chance_corrigida"] = corrigida(r["idade"])
        r["chance_prd"] = prd(r["idade"])
        r["nunca_fechou"] = r["close_date"].isna()
        partes.append(r)
    return pd.concat(partes, ignore_index=True)


def _avaliar(escolhas, ganhou, perdeu, nunca, receita, n_semanas):
    """escolhas: lista de (semana, ids). Na receita, cada deal conta uma vez só."""
    ids = np.concatenate([e for _, e in escolhas])
    semana = np.concatenate([np.full(len(e), w) for w, e in escolhas])
    unicos, primeira = np.unique(ids, return_index=True)
    receita_semana = np.bincount(semana[primeira], weights=receita[unicos], minlength=n_semanas)
    metricas = {
        "deals": len(unicos),
        "vitorias": int(ganhou[unicos].sum()),
        "receita": float(receita[unicos].sum()),
        "semanas_foco": len(ids),
        "semanas_ganho": int(ganhou[ids].sum()),
        "semanas_perda": int(perdeu[ids].sum()),
        "semanas_nunca": int(nunca[ids].sum()),
    }
    return metricas, receita_semana


def simular_segundas(base, inicio=None, fim=None, n=None, rodadas=None, semente=None) -> Simulacao:
    """A/B do vendedor: mesmas segundas, mesma capacidade, quatro jeitos de escolher.

    - Com Clima: os n deals de maior valor esperado (chance x preço).
    - Curva do PRD: igual, com a chance da versão 1 (para comparação).
    - Maior valor: os n deals de preço mais alto.
    - Sorteio: n deals ao acaso, repetido várias vezes (o feeling sem informação).
    """
    segundas = pd.date_range(inicio or config.SIM_INICIO, fim or config.SIM_FIM, freq="W-MON")
    n = n or config.SIM_DEALS_POR_SEMANA
    rodadas = rodadas or config.SIM_RODADAS_SORTEIO
    rng = np.random.default_rng(config.SIM_SEMENTE if semente is None else semente)

    deals = base.deals
    ganhou = deals["ganhou"].to_numpy()
    perdeu = deals["deal_stage"].eq("Lost").to_numpy()
    nunca = deals["close_date"].isna().to_numpy()
    receita = np.where(ganhou, deals["close_value"].fillna(0).to_numpy(), 0.0)
    posicao = pd.Series(np.arange(len(deals)), index=deals["opportunity_id"])

    ret = retratos_das_segundas(base, segundas)
    ret["pos"] = posicao.loc[ret["opportunity_id"]].to_numpy()
    chance_clima = "chance_corrigida" if config.CURVA == "corrigida" else "chance_prd"
    ret["nota_clima"] = ret[chance_clima] * ret["sales_price"]
    ret["nota_clima_prd"] = ret["chance_prd"] * ret["sales_price"]
    criterios = {"clima": "nota_clima", "clima_prd": "nota_clima_prd", "maior_valor": "sales_price"}
    semana_de = {s: i for i, s in enumerate(segundas)}
    n_semanas = len(segundas)

    linhas, acumulado = [], {k: np.zeros(n_semanas) for k in ESTRATEGIAS}
    for vendedor, g in ret.groupby("sales_agent", sort=True):
        escolhas = {k: [] for k in criterios}
        sorteios = []
        for segunda, gs in g.groupby("segunda", sort=True):
            w, k, pos = semana_de[segunda], min(n, len(gs)), gs["pos"].to_numpy()
            for est, coluna in criterios.items():
                ordem = np.argsort(-gs[coluna].to_numpy(), kind="stable")[:k]
                escolhas[est].append((w, pos[ordem]))
            aleatorio = rng.random((rodadas, len(gs))).argsort(axis=1)[:, :k]
            sorteios.append((w, pos[aleatorio]))
        for est, esc in escolhas.items():
            m, rs = _avaliar(esc, ganhou, perdeu, nunca, receita, n_semanas)
            linhas.append({"estrategia": est, "vendedor": vendedor, **m})
            acumulado[est] += rs
        medidas, rs_total = [], np.zeros(n_semanas)
        for r in range(rodadas):
            m, rs = _avaliar([(w, e[r]) for w, e in sorteios], ganhou, perdeu, nunca, receita, n_semanas)
            medidas.append(m)
            rs_total += rs
        linhas.append({"estrategia": "sorteio", "vendedor": vendedor, **pd.DataFrame(medidas).mean().to_dict()})
        acumulado["sorteio"] += rs_total / rodadas

    pv = pd.DataFrame(linhas)
    nv = pv["vendedor"].nunique()
    somas = ["deals", "vitorias", "receita", "semanas_foco", "semanas_ganho", "semanas_perda", "semanas_nunca"]
    resumo = pv.groupby("estrategia")[somas].sum().reindex(list(ESTRATEGIAS))
    resumo["acerto_semanas"] = resumo["semanas_ganho"] / resumo["semanas_foco"]
    resumo["tempo_perda"] = resumo["semanas_perda"] / resumo["semanas_foco"]
    resumo["tempo_nunca_fecha"] = resumo["semanas_nunca"] / resumo["semanas_foco"]
    resumo["receita_por_deal"] = resumo["receita"] / resumo["deals"]
    resumo["receita_por_hora_foco"] = resumo["receita"] / (nv * n_semanas * config.HORAS_POR_SEMANA)
    resumo["horas_semana_deal_morto"] = resumo["tempo_nunca_fecha"] * config.HORAS_POR_SEMANA
    resumo["vs_feeling"] = resumo["receita"] / resumo.loc["sorteio", "receita"] - 1
    resumo["vs_maior_valor"] = resumo["receita"] / resumo.loc["maior_valor", "receita"] - 1
    resumo.insert(0, "nome", [ESTRATEGIAS[k] for k in resumo.index])

    tabela = pv.pivot(index="vendedor", columns="estrategia", values="receita")
    comparacoes = []
    for outro in ("maior_valor", "sorteio", "clima_prd"):
        ganho = tabela["clima"] / tabela[outro] - 1
        comparacoes.append({
            "contra": ESTRATEGIAS[outro],
            "vendedores_em_que_o_clima_ganha": int((ganho > 0).sum()),
            "vendedores": int(len(ganho)),
            "ganho_mediano": float(ganho.median()),
        })
    acum = pd.DataFrame({ESTRATEGIAS[k]: np.cumsum(v) / nv for k, v in acumulado.items()}, index=segundas)
    return Simulacao(segundas, sorted(pv["vendedor"].unique()), ret, pv, resumo,
                     pd.DataFrame(comparacoes), acum)


# ---------------------------------------------------------------------------
# Nota de ordenação e calibração
# ---------------------------------------------------------------------------
def nota_ordenacao(retratos: pd.DataFrame) -> dict:
    """Nota de 0,5 (cara ou coroa) a 1 (acerta sempre): a curva põe na frente quem ganha?"""
    y = retratos["ganhou"].to_numpy()
    n1, n0 = y.sum(), len(y) - y.sum()
    notas = {}
    for tipo in ("corrigida", "prd"):
        posto = retratos[f"chance_{tipo}"].rank().to_numpy()
        notas[tipo] = float((posto[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
    return notas


def calibracao(retratos: pd.DataFrame) -> pd.DataFrame:
    """Chance prevista contra o que aconteceu, por faixa de idade do deal."""
    r = retratos.assign(faixa=pd.cut(retratos["idade"], FAIXAS_IDADE, labels=ROTULOS_FAIXA))
    return r.groupby("faixa", observed=True).agg(
        casos=("idade", "size"),
        chance_corrigida=("chance_corrigida", "mean"),
        chance_prd=("chance_prd", "mean"),
        ganhou_de_fato=("ganhou", "mean"),
        nunca_fechou=("nunca_fechou", "mean"),
    )


# ---------------------------------------------------------------------------
# Autoteste dos indicadores
# ---------------------------------------------------------------------------
def _tercil(valores: pd.Series, rotulos) -> pd.Series:
    return pd.qcut(valores, 3, labels=rotulos).astype(object)


def _acima_abaixo(taxas: pd.Series) -> pd.Series:
    rotulo = np.where(taxas >= taxas.median(), "acima da mediana", "abaixo da mediana")
    return pd.Series(rotulo, index=taxas.index)


def indicadores(base, corte) -> pd.DataFrame:
    """Cada indicador vira uma coluna de grupos. Deal sem conta fica vazio nos de conta."""
    corte = pd.Timestamp(corte)
    d = base.deals.copy()
    contas = base.contas.set_index("account")
    d["setor"] = d["sector"]
    d["porte"] = d["account"].map(_tercil(contas["revenue"], ["pequena", "média", "grande"]))
    d["funcionarios"] = d["account"].map(_tercil(contas["employees"], ["poucos", "médio", "muitos"]))
    d["idade_da_conta"] = d["account"].map(_tercil(contas["year_established"], ["mais antiga", "média", "mais nova"]))
    d["faz_parte_de_grupo"] = np.where(d["sem_conta"], None, np.where(d["subsidiary_of"].notna(), "sim", "não"))
    d["sede"] = np.where(d["sem_conta"], None, np.where(d["office_location"].eq("United States"), "EUA", "fora dos EUA"))
    d["regiao"] = d["regional_office"]
    d["gerente"] = d["manager"]

    # Históricos: só com o que já tinha fechado antes do corte.
    passado = d[d["close_date"].notna() & (d["close_date"] < corte)]
    d["historico_do_vendedor"] = d["sales_agent"].map(_acima_abaixo(passado.groupby("sales_agent")["ganhou"].mean()))
    por_conta = passado.groupby("account")["ganhou"].agg(["mean", "size"])
    d["historico_da_conta"] = d["account"].map(_acima_abaixo(por_conta.loc[por_conta["size"] >= 5, "mean"]))

    # Relacionamento: há quantos dias a conta tinha comprado quando este deal
    # engajou? O limite é a mediana do passado (antes do corte).
    ganhos = d.loc[d["ganhou"], ["account", "close_date"]]
    recencia = pd.Series(np.nan, index=d.index)
    alvo = d[d["account"].notna() & d["engage_date"].notna()]
    for conta, g in alvo.groupby("account"):
        datas = np.sort(ganhos.loc[ganhos["account"] == conta, "close_date"].to_numpy())
        if not len(datas):
            continue
        engage = g["engage_date"].to_numpy()
        i = np.searchsorted(datas, engage, side="left")
        dias = (engage - datas[np.maximum(i - 1, 0)]) / np.timedelta64(1, "D")
        recencia.loc[g.index] = np.where(i > 0, dias, np.nan)
    limite = recencia.loc[passado.index].median()
    d["relacionamento"] = np.where(
        d["sem_conta"] | d["engage_date"].isna(), None,
        np.where(recencia <= limite, "comprou há pouco", "comprou há mais tempo"))
    return d


def autoteste(base, corte=None, fim=None) -> pd.DataFrame:
    """Aprende com o que fechou antes do corte; testa nos deals que engajaram depois.

    Um indicador só liga se o grupo que era melhor no passado continuar melhor
    no futuro, com 5 pontos de diferença ou mais e 200 casos ou mais por lado.
    """
    corte = pd.Timestamp(corte or config.AUTOTESTE_CORTE)
    fim = pd.Timestamp(fim or config.AUTOTESTE_FIM)
    d = indicadores(base, corte)
    treino = d[d["close_date"].notna() & (d["close_date"] < corte)]
    teste = d[d["engage_date"].notna() & (d["engage_date"] >= corte) & (d["engage_date"] <= fim)]
    linhas = []
    for ind in INDICADORES:
        tr, te = treino.dropna(subset=[ind]), teste.dropna(subset=[ind])
        taxa = tr.groupby(ind)["ganhou"].mean()
        melhores = set(taxa[taxa >= tr["ganhou"].mean()].index)
        grupo = te[ind].isin(melhores)
        a, b = te.loc[grupo, "ganhou"], te.loc[~grupo, "ganhou"]
        linha = {"indicador": ind, "grupos_melhores": ", ".join(sorted(map(str, melhores))),
                 "casos_melhores": len(a), "casos_outros": len(b)}
        if not melhores or len(melhores) == len(taxa) or a.empty or b.empty:
            linhas.append({**linha, "diferenca": np.nan, "status": "desligado"})
            continue
        dif = a.mean() - b.mean()
        if min(len(a), len(b)) >= config.AUTOTESTE_MIN_CASOS and dif >= config.AUTOTESTE_LIMIAR:
            status = "ligado"
        elif dif >= config.AUTOTESTE_OBSERVACAO:
            status = "em observação"
        else:
            status = "desligado"
        linhas.append({**linha, "acerto_melhores": a.mean(), "acerto_outros": b.mean(),
                       "diferenca": dif, "status": status})
    resultado = pd.DataFrame(linhas).set_index("indicador")
    resultado["muda_a_lista_do_vendedor"] = ~resultado.index.isin(IGUAIS_NO_VENDEDOR)
    resultado["uso_sugerido"] = np.select(
        [
            resultado["status"].eq("ligado") & resultado["muda_a_lista_do_vendedor"],
            resultado["status"].eq("ligado"),
            resultado["status"].eq("em observação"),
        ],
        ["candidato ao Score (Hugo decide)", "visão do gerente", "em observação"],
        default="fora",
    )
    return resultado


# ---------------------------------------------------------------------------
# Produtividade por vendedor e por hora
# ---------------------------------------------------------------------------
def produtividade_mensal(base):
    """Fechamentos, vitórias e receita por vendedor e mês; receita por hora (8h por dia útil)."""
    fechados = base.deals[~base.deals["aberto"]].copy()
    fechados["mes"] = fechados["close_date"].dt.to_period("M")
    fechados["receita"] = np.where(fechados["ganhou"], fechados["close_value"], 0.0)
    vendedores = sorted(base.deals["sales_agent"].unique())
    meses = pd.period_range(fechados["mes"].min(), fechados["mes"].max(), freq="M")
    grade = pd.MultiIndex.from_product([meses, vendedores], names=["mes", "vendedor"])
    v = (
        fechados.groupby(["mes", "sales_agent"])
        .agg(fechados=("ganhou", "size"), vitorias=("ganhou", "sum"), receita=("receita", "sum"))
        .rename_axis(["mes", "vendedor"])
        .reindex(grade, fill_value=0)
        .reset_index()
    )
    dias = pd.Series({m: int(np.busday_count(m.start_time.date(), (m.end_time + pd.Timedelta(days=1)).date()))
                      for m in meses})
    v["horas"] = v["mes"].map(dias) * config.HORAS_POR_DIA
    v["receita_por_hora"] = v["receita"] / v["horas"]
    mensal = v.groupby("mes").agg(
        fechados_media=("fechados", "mean"),
        vitorias_media=("vitorias", "mean"),
        vitorias_mediana=("vitorias", "median"),
        receita_media=("receita", "mean"),
        receita_mediana=("receita", "median"),
        receita_hora_media=("receita_por_hora", "mean"),
        receita_hora_mediana=("receita_por_hora", "median"),
    )
    mensal.insert(0, "dias_uteis", dias)
    return mensal, v


def resumo_produtividade(base) -> dict:
    mensal, v = produtividade_mensal(base)
    total = v.groupby("vendedor")[["fechados", "vitorias", "receita", "horas"]].sum()
    meses = v["mes"].nunique()
    semanas = mensal["dias_uteis"].sum() / 5
    return {
        "vendedores": len(total),
        "fechados_por_mes": total["fechados"].mean() / meses,
        "fechados_por_semana": total["fechados"].sum() / len(total) / semanas,
        "vitorias_por_mes_media": total["vitorias"].mean() / meses,
        "vitorias_por_mes_mediana": total["vitorias"].median() / meses,
        "receita_por_mes_media": total["receita"].mean() / meses,
        "receita_por_mes_mediana": total["receita"].median() / meses,
        "receita_por_hora_media": total["receita"].sum() / total["horas"].sum(),
        "receita_por_hora_mediana": (total["receita"] / total["horas"]).median(),
    }


def equivalencia_por_hora(mensal: pd.DataFrame, ganho: float) -> pd.DataFrame:
    """Cenário: o ganho da lista vale para todo o tempo do vendedor (premissa explícita)."""
    e = mensal[["dias_uteis", "receita_hora_media"]].rename(columns={"receita_hora_media": "hoje"})
    e["com_clima"] = e["hoje"] * (1 + ganho)
    return e


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------
def relatorio(base=None) -> None:
    from lead_scorer import dados

    base = base or dados.carregar()
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    sim = simular_segundas(base)
    print(f"Simulação: {len(sim.segundas)} segundas, {len(sim.vendedores)} vendedores, "
          f"{config.SIM_DEALS_POR_SEMANA} deals por semana\n")
    print(sim.resumo.round(3).to_string(), "\n")
    print(sim.vendedor_a_vendedor.round(3).to_string(), "\n")
    print("Nota de ordenação:", {k: round(v, 3) for k, v in nota_ordenacao(sim.retratos).items()}, "\n")
    print(calibracao(sim.retratos).round(3).to_string(), "\n")
    print(autoteste(base).round(3).to_string(), "\n")
    mensal, _ = produtividade_mensal(base)
    print(mensal.round(1).to_string(), "\n")
    print({k: round(v, 2) for k, v in resumo_produtividade(base).items()}, "\n")
    print(equivalencia_por_hora(mensal, sim.resumo.loc["clima", "vs_feeling"]).round(1).to_string())


if __name__ == "__main__":
    relatorio()
