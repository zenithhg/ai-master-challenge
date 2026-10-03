"""Raio X do Cliente: ficha da conta, produto do porte e matemática do 1%.

Analogia: a ficha de um jogador no scout de futebol. Antes de entrar em campo
(a ligação), o vendedor vê o histórico do cliente, o que contas do mesmo porte
compram e quanto o preço pesa no faturamento dele.
"""
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lead_scorer.score import porcento

FAIXAS = ("pequena", "média", "grande")
AVISO_SEM_CONTA = "Complete o cadastro para ver o Raio X."
LIMITE_1PCT = 0.01  # Alfredo Soares: até 1% do faturamento, o preço cabe no bolso


@dataclass
class Ficha:
    """Ficha da conta no estilo scout, com o histórico até a data de referência."""

    conta: str
    setor: str
    porte: str
    receita_milhoes: float
    funcionarios: int
    sede: str
    grupo: str | None
    negociacoes: int
    vitorias: int
    derrotas: int
    abertas: int
    aproveitamento: float           # vitórias / fechadas (NaN se nunca fechou)
    media_do_time: float            # aproveitamento de todo o time
    ultimos_5: list                 # "V" ou "D", do mais antigo ao mais recente
    produto_mais_comprado: str | None
    ticket_medio: float             # valor médio das vitórias (NaN se nunca ganhou)
    dias_desde_ultima_compra: int | None
    vendedores: list


@dataclass
class ProdutoDoPorte:
    """Mix de produtos ganhos por faixa de faturamento da conta."""

    mix: pd.DataFrame          # fração das vitórias de cada produto, por faixa
    ticket_medio: pd.Series    # valor médio das vitórias, por faixa
    p_valor: float             # abaixo de 0,05: a diferença entre faixas é real
    p_valor_setor: float       # o mesmo teste por setor, como controle
    cortes: np.ndarray         # limites das faixas, em milhões de US$


@dataclass
class RaioX:
    """Tudo o que a aba do deal mostra. Deal sem conta só traz o aviso."""

    opportunity_id: str
    aviso: str | None = None
    ficha: Ficha | None = None
    mix_do_porte: pd.Series | None = None
    ticket_do_porte: float | None = None
    peso_no_faturamento: float | None = None
    frase_1pct: str | None = None


def _cauda_qui2(x: float, gl: int) -> float:
    """Chance de um qui-quadrado com `gl` graus de liberdade passar de `x` (fórmula exata)."""
    if x <= 0:
        return 1.0
    k, p = (2, math.exp(-x / 2)) if gl % 2 == 0 else (1, math.erfc(math.sqrt(x / 2)))
    while k < gl:
        p += math.exp(k / 2 * math.log(x / 2) - x / 2 - math.lgamma(k / 2 + 1))
        k += 2
    return min(p, 1.0)


def p_valor_qui2(tabela: pd.DataFrame) -> float:
    """Teste qui-quadrado: chance de uma diferença dessas aparecer por acaso."""
    obs = tabela.to_numpy(dtype=float)
    obs = obs[obs.sum(axis=1) > 0][:, obs.sum(axis=0) > 0]
    esperado = obs.sum(axis=1, keepdims=True) * obs.sum(axis=0, keepdims=True) / obs.sum()
    x = float(((obs - esperado) ** 2 / esperado).sum())
    return _cauda_qui2(x, (obs.shape[0] - 1) * (obs.shape[1] - 1))


def _vitorias_ate_a_referencia(base) -> pd.DataFrame:
    """Vitórias já fechadas até a data de referência (nada do futuro, como no Clima)."""
    fechadas = base.deals["ganhou"] & (base.deals["close_date"] <= base.data_ref)
    return base.deals[fechadas]


def cortes_de_porte(base) -> np.ndarray:
    """Divide as vitórias em 3 grupos do mesmo tamanho pelo faturamento da conta."""
    receita = _vitorias_ate_a_referencia(base)["revenue"].dropna()
    return np.concatenate([[-np.inf], receita.quantile([1 / 3, 2 / 3]).to_numpy(), [np.inf]])


def porte(receita_milhoes, cortes: np.ndarray):
    """Faixa de porte (pequena, média ou grande) de um ou vários faturamentos."""
    faixas = pd.cut(np.atleast_1d(receita_milhoes), cortes, labels=list(FAIXAS))
    return faixas[0] if np.ndim(receita_milhoes) == 0 else faixas


def produto_do_porte(base) -> ProdutoDoPorte:
    """O que contas de cada porte compram, com o teste de que a diferença é real."""
    cortes = cortes_de_porte(base)
    vitorias = _vitorias_ate_a_referencia(base).dropna(subset=["revenue"])
    faixa = pd.Series(porte(vitorias["revenue"].to_numpy(), cortes), index=vitorias.index)
    tabela = pd.crosstab(faixa, vitorias["product"])
    return ProdutoDoPorte(
        mix=tabela.div(tabela.sum(axis=1), axis=0),
        ticket_medio=vitorias.groupby(faixa, observed=True)["close_value"].mean(),
        p_valor=p_valor_qui2(tabela),
        p_valor_setor=p_valor_qui2(pd.crosstab(vitorias["sector"], vitorias["product"])),
        cortes=cortes,
    )


def peso_no_faturamento(preco, receita_milhoes):
    """Preço do produto dividido pelo faturamento anual da conta (revenue em milhões de US$)."""
    return preco / (receita_milhoes * 1e6)


def frase_1pct(produto: str, preco: float, receita_milhoes: float) -> str:
    """Matemática do 1% em frase de vendedor."""
    peso = peso_no_faturamento(preco, receita_milhoes)
    texto = "menos de 0,01%" if peso < 0.0001 else porcento(peso, 2)
    if peso < LIMITE_1PCT:
        return f"{produto} custa {texto} do faturamento anual da conta. Abaixo de 1%: o preço cabe no bolso."
    return f"{produto} custa {texto} do faturamento anual da conta. Acima de 1%: mostre o retorno antes do preço."


def ficha(base, conta: str, cortes: np.ndarray | None = None) -> Ficha:
    """Ficha scout da conta: negociações, resultados, produto e quem já atendeu."""
    deals = base.deals
    ate_a_referencia = deals["engage_date"].isna() | (deals["engage_date"] <= base.data_ref)
    da_conta = deals[deals["account"].eq(conta) & ate_a_referencia]
    if da_conta.empty:
        raise KeyError(f"Conta sem negociações: {conta}")
    cortes = cortes if cortes is not None else cortes_de_porte(base)
    info = base.contas.set_index("account").loc[conta]

    def fechadas_de(d):
        return d[d["close_date"].notna() & (d["close_date"] <= base.data_ref)]

    fechadas = fechadas_de(da_conta).sort_values(["close_date", "opportunity_id"])
    vitorias = fechadas[fechadas["ganhou"]]
    contagem = vitorias["product"].value_counts()
    mais_comprado = min(contagem.index, key=lambda p: (-contagem[p], p)) if len(contagem) else None

    return Ficha(
        conta=conta,
        setor=info["sector"],
        porte=porte(info["revenue"], cortes),
        receita_milhoes=float(info["revenue"]),
        funcionarios=int(info["employees"]),
        sede=info["office_location"],
        grupo=info["subsidiary_of"] if pd.notna(info["subsidiary_of"]) else None,
        negociacoes=len(da_conta),
        vitorias=len(vitorias),
        derrotas=len(fechadas) - len(vitorias),
        abertas=len(da_conta) - len(fechadas),
        aproveitamento=vitorias.shape[0] / len(fechadas) if len(fechadas) else float("nan"),
        media_do_time=float(fechadas_de(deals)["ganhou"].mean()),
        ultimos_5=["V" if g else "D" for g in fechadas["ganhou"].tail(5)],
        produto_mais_comprado=mais_comprado,
        ticket_medio=float(vitorias["close_value"].mean()) if len(vitorias) else float("nan"),
        dias_desde_ultima_compra=(
            int((base.data_ref - vitorias["close_date"].max()).days) if len(vitorias) else None
        ),
        vendedores=sorted(da_conta["sales_agent"].unique()),
    )


def raio_x(base, opportunity_id: str, do_porte: ProdutoDoPorte | None = None) -> RaioX:
    """Monta o Raio X de um deal. Passe `do_porte` pronto para não recalcular."""
    achados = base.deals[base.deals["opportunity_id"].eq(opportunity_id)]
    if achados.empty:
        raise KeyError(f"Deal não encontrado: {opportunity_id}")
    deal = achados.iloc[0]
    if pd.isna(deal["account"]):
        return RaioX(opportunity_id, aviso=AVISO_SEM_CONTA)

    do_porte = do_porte or produto_do_porte(base)
    f = ficha(base, deal["account"], do_porte.cortes)
    return RaioX(
        opportunity_id,
        ficha=f,
        mix_do_porte=do_porte.mix.loc[f.porte],
        ticket_do_porte=float(do_porte.ticket_medio.loc[f.porte]),
        peso_no_faturamento=peso_no_faturamento(deal["sales_price"], deal["revenue"]),
        frase_1pct=frase_1pct(deal["product"], deal["sales_price"], deal["revenue"]),
    )
