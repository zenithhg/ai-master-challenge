"""Fase 3: Raio X do Cliente (ficha, produto do porte e matemática do 1%)."""
from dataclasses import replace

import pandas as pd
import pytest

from lead_scorer import raio_x


@pytest.fixture(scope="module")
def do_porte(base):
    return raio_x.produto_do_porte(base)


def test_produto_do_porte_bate_com_o_prd(do_porte):
    mix = do_porte.mix
    assert mix.loc["pequena", "MG Special"] == pytest.approx(0.232, abs=0.001)
    assert mix.loc["grande", "MG Special"] == pytest.approx(0.144, abs=0.001)
    assert mix.loc["grande", "MG Advanced"] == pytest.approx(0.176, abs=0.001)
    assert mix.loc["pequena", "MG Advanced"] == pytest.approx(0.132, abs=0.001)
    assert round(do_porte.ticket_medio["grande"]) == 2541
    assert round(do_porte.ticket_medio["pequena"]) == 2237
    assert do_porte.p_valor < 0.001        # porte muda o mix
    assert do_porte.p_valor_setor > 0.05   # setor não muda


def test_qui_quadrado_bate_com_a_tabela():
    # valores críticos de 5% e 0,1% das tabelas de qui-quadrado
    assert raio_x._cauda_qui2(3.841, 1) == pytest.approx(0.05, abs=0.001)
    assert raio_x._cauda_qui2(7.815, 3) == pytest.approx(0.05, abs=0.001)
    assert raio_x._cauda_qui2(21.026, 12) == pytest.approx(0.05, abs=0.001)
    assert raio_x._cauda_qui2(32.909, 12) == pytest.approx(0.001, abs=0.0001)


def test_matematica_do_1pct(base):
    com_conta = base.deals.dropna(subset=["revenue"])
    peso = raio_x.peso_no_faturamento(com_conta["sales_price"], com_conta["revenue"])
    assert peso.max() == pytest.approx(0.00121, abs=0.00001)   # máximo da base: 0,12%
    assert raio_x.frase_1pct("GTX Plus Pro", 5482, 4.54) == (
        "GTX Plus Pro custa 0,12% do faturamento anual da conta. Abaixo de 1%: o preço cabe no bolso."
    )
    assert "Acima de 1%" in raio_x.frase_1pct("GTK 500", 26768, 1.0)


def test_ficha_da_conta(base, do_porte):
    conta = base.deals.loc[base.deals["ganhou"], "account"].value_counts().index[0]
    f = raio_x.ficha(base, conta, do_porte.cortes)
    assert f.vitorias + f.derrotas + f.abertas == f.negociacoes
    assert f.aproveitamento == pytest.approx(f.vitorias / (f.vitorias + f.derrotas))
    assert f.media_do_time == pytest.approx(0.6315, abs=0.0001)
    assert len(f.ultimos_5) == 5 and set(f.ultimos_5) <= {"V", "D"}
    assert f.porte in raio_x.FAIXAS
    assert f.dias_desde_ultima_compra >= 0

    # o último resultado da ficha é o fechamento mais recente da conta
    fechadas = base.deals[base.deals["account"].eq(conta) & base.deals["close_date"].notna()]
    ultima = fechadas.sort_values(["close_date", "opportunity_id"]).iloc[-1]
    assert f.ultimos_5[-1] == ("V" if ultima["ganhou"] else "D")


def test_deal_sem_conta_mostra_aviso(base):
    sem_conta = base.deals.loc[base.deals["sem_conta"], "opportunity_id"].iloc[0]
    r = raio_x.raio_x(base, sem_conta)
    assert r.aviso == raio_x.AVISO_SEM_CONTA
    assert r.ficha is None


def test_raio_x_de_deal_com_conta(base, do_porte):
    abertos = base.deals[base.deals["aberto"] & ~base.deals["sem_conta"]]
    r = raio_x.raio_x(base, abertos["opportunity_id"].iloc[0], do_porte)
    assert r.aviso is None
    assert r.mix_do_porte.sum() == pytest.approx(1.0)
    assert r.peso_no_faturamento <= 0.00121
    assert r.frase_1pct.endswith("o preço cabe no bolso.")


def test_nada_do_futuro_entra_no_produto_do_porte(base):
    """Com data de referência em 01/07/2017, vitórias fechadas depois não podem contar."""
    ref = pd.Timestamp("2017-07-01")
    vitorias_depois = base.deals["ganhou"] & (base.deals["close_date"] > ref)
    assert vitorias_depois.sum() > 0  # só prova algo se houver o que vazar

    base_ref = replace(base, data_ref=ref)
    base_sem_futuro = replace(base, deals=base.deals[~vitorias_depois], data_ref=ref)
    com_e_sem_o_futuro = raio_x.produto_do_porte(base_ref), raio_x.produto_do_porte(base_sem_futuro)

    assert com_e_sem_o_futuro[0].mix.equals(com_e_sem_o_futuro[1].mix)
    assert com_e_sem_o_futuro[0].ticket_medio.equals(com_e_sem_o_futuro[1].ticket_medio)
    assert com_e_sem_o_futuro[0].cortes.tolist() == com_e_sem_o_futuro[1].cortes.tolist()


def test_nada_do_futuro_entra_na_ficha(base):
    """Com data de referência em 01/07/2017, deal que só engaja depois não pode contar na ficha."""
    ref = pd.Timestamp("2017-07-01")
    tem_antes = base.deals["engage_date"].isna() | (base.deals["engage_date"] <= ref)
    tem_depois = base.deals["engage_date"] > ref

    contas_com_antes = base.deals.loc[tem_antes, "account"].dropna().unique()
    conta = base.deals.loc[tem_depois & base.deals["account"].isin(contas_com_antes), "account"].value_counts().index[0]

    base_ref = replace(base, data_ref=ref)
    base_sem_futuro = replace(base, deals=base.deals[~tem_depois], data_ref=ref)
    f = raio_x.ficha(base_ref, conta)
    f_sem_futuro = raio_x.ficha(base_sem_futuro, conta)

    assert f.negociacoes == f_sem_futuro.negociacoes
    assert f.abertas == f_sem_futuro.abertas
    assert f.vendedores == f_sem_futuro.vendedores
    assert f.negociacoes < len(base.deals[base.deals["account"].eq(conta)])  # prova que havia o que vazar
