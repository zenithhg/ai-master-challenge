"""Verificação do fator carga: ele melhora a escolha dos deals da semana?

Rodar dentro de solution/:  python analises/fator_carga.py

Reusa a simulação oficial das segundas (lead_scorer.validacao) sem alterá-la:
troca só a coluna de chance da estratégia de comparação pela chance com carga.
Assim, "Com Clima" continua sendo a chance só pela idade, e a linha
"Idade + carga" é a chance que o app usa (clima.aplicar).

Também mede a diferença de taxa de ganho entre vendedores com pouca e com
muita carga, em três datas de corte, só com deals já fechados em cada data.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

import config
from lead_scorer import clima, dados
from lead_scorer import validacao as v

base = dados.carregar()
deals = base.deals


def carga_no_engage(deals: pd.DataFrame) -> pd.Series:
    """Deals abertos do mesmo vendedor no dia do engage (mesma regra de clima.aplicar)."""
    carga = pd.Series(np.nan, index=deals.index)
    validos = deals[deals["engage_date"].notna() & deals["sales_agent"].notna()]
    for agente, g in validos.groupby("sales_agent"):
        todos = deals[deals["sales_agent"] == agente]
        inicio = todos["engage_date"].to_numpy(dtype="datetime64[ns]")
        fim = todos["close_date"].to_numpy(dtype="datetime64[ns]")
        dia = g["engage_date"].to_numpy(dtype="datetime64[ns]")
        engajado = inicio[None, :] <= dia[:, None]
        aberto = np.isnat(fim)[None, :] | (fim[None, :] > dia[:, None])
        carga.loc[g.index] = (engajado & aberto).sum(axis=1)
    return carga


carga = carga_no_engage(deals)
carga_por_id = pd.Series(carga.to_numpy(), index=deals["opportunity_id"])


def faixas(valores: np.ndarray, referencia: np.ndarray) -> np.ndarray:
    """Tercil de carga (0 baixa, 1 média, 2 alta); sem carga conta como média."""
    p33, p66 = np.percentile(referencia[~np.isnan(referencia)], [33, 66])
    return np.where(np.isnan(valores), 1, np.select([valores <= p33, valores <= p66], [0, 1], 2))


def fator_na_data(data):
    """Taxa de ganho por tercil, aprendida só com deals fechados até a data."""
    fechados = clima._fechados_ate(deals, data) & deals["engage_date"].notna()
    c = carga[fechados].to_numpy()
    faixa = faixas(c, c)
    ganhou = deals.loc[fechados, "ganhou"].to_numpy()
    taxa = np.array([ganhou[faixa == k].mean() if (faixa == k).any() else config.PISO_CHANCE
                     for k in range(3)])
    return np.maximum(taxa / ganhou.mean(), config.PISO_CHANCE), taxa


retratos_originais = v.retratos_das_segundas


def retratos_com_carga(base_, segundas):
    r = retratos_originais(base_, segundas)
    chance = np.empty(len(r))
    for segunda, idx in r.groupby("segunda").groups.items():
        fator, _ = fator_na_data(segunda)
        c = carga_por_id.loc[r.loc[idx, "opportunity_id"]].to_numpy()
        chance[r.index.get_indexer(idx)] = np.clip(
            r.loc[idx, "chance_corrigida"].to_numpy() * fator[faixas(c, c)], config.PISO_CHANCE, 1.0
        )
    r["chance_prd"] = chance  # a estratégia de comparação passa a ser "idade + carga"
    return r


if __name__ == "__main__":
    ap = clima.aplicar(base)
    confere = ap[["opportunity_id", "carga_pipeline"]].dropna()
    diferenca = np.abs(confere["carga_pipeline"].to_numpy()
                       - carga_por_id.loc[confere["opportunity_id"]].to_numpy()).max()
    print(f"Carga igual à do app (diferença máxima): {diferenca:.0f}\n")

    v.retratos_das_segundas = retratos_com_carga
    sim = v.simular_segundas(base)
    resumo = sim.resumo.copy()
    resumo.loc["clima", "nome"] = "Só idade (simulação oficial)"
    resumo.loc["clima_prd", "nome"] = "Idade + carga (como no app)"
    print(resumo[["nome", "receita", "acerto_semanas", "vs_feeling", "vs_maior_valor"]]
          .round(3).to_string(), "\n")
    nota = v.nota_ordenacao(sim.retratos)
    print("Nota de ordenação (0,5 = sorteio):",
          {"só idade": round(nota["corrigida"], 3), "idade + carga": round(nota["prd"], 3)}, "\n")

    for corte in ["2017-06-30", "2017-09-30", "2017-12-31"]:
        _, taxa = fator_na_data(pd.Timestamp(corte))
        print(f"Corte {corte}: taxa de ganho baixa/média/alta carga = "
              f"{np.round(taxa, 3)}  diferença baixa - alta = {100 * (taxa[0] - taxa[2]):+.1f} pp")
