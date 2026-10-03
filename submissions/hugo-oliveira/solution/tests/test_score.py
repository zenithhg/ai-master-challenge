"""Fase 3: Score, rótulos de ação, selos e frase na data de referência (31/12/2017)."""
import numpy as np
import pytest

from lead_scorer import clima, score
from lead_scorer.score import ATACAR, CADASTRO, FECHAR, LIMPAR, NUTRICAO, QUALIFICAR


@pytest.fixture(scope="module")
def pontuados(base):
    return score.pontuar(base)


def test_rotulos_batem_com_o_prd(pontuados):
    tabela = score.distribuicao(pontuados)
    assert tabela["deals"].to_dict() == {
        ATACAR: 120, FECHAR: 171, QUALIFICAR: 507, NUTRICAO: 180, LIMPAR: 232, CADASTRO: 879,
    }
    # valor a preço de tabela, em milhares de US$
    assert (tabela["valor"] / 1000).round().to_dict() == {
        ATACAR: 583, FECHAR: 94, QUALIFICAR: 1090, NUTRICAO: 935, LIMPAR: 130, CADASTRO: 2134,
    }


def test_selo_esfriando(pontuados):
    esfriando = pontuados[pontuados["selo_esfriando"]]
    assert len(esfriando) == 188
    assert esfriando["rotulo"].value_counts().to_dict() == {FECHAR: 105, ATACAR: 83}


def test_selo_sem_cadastro(pontuados):
    assert pontuados["selo_sem_cadastro"].sum() == 1425
    firmes = pontuados["rotulo"].isin(score.FOCO)
    assert firmes.sum() == 291
    assert (firmes & pontuados["selo_sem_cadastro"]).sum() == 204


def test_score_e_a_posicao_do_valor_esperado(pontuados):
    ve = pontuados["valor_esperado"].to_numpy()
    menores = (ve[:, None] > ve[None, :]).sum(axis=1)
    assert (pontuados["score"].to_numpy() == np.floor(100 * menores / len(ve))).all()
    assert pontuados["score"].between(0, 100).all()
    assert pontuados["score"].is_monotonic_decreasing


def test_frase_do_prd():
    texto = score.frase(clima.ATIVO, 45, 0.479, 4821, ATACAR)
    assert texto == (
        "Deals como este, abertos há 45 dias, terminaram ganhos 48% das vezes. "
        "Vale $4.821. Valor esperado: $2.309. Consulta médica e proposta."
    )


def test_todo_deal_tem_frase_com_o_que_fazer(pontuados):
    for rotulo, acao in score.O_QUE_FAZER.items():
        frases = pontuados.loc[pontuados["rotulo"].eq(rotulo), "frase"]
        assert frases.str.endswith(acao).all(), rotulo
    prospects = pontuados["estado"].eq(clima.A_QUALIFICAR)
    assert pontuados.loc[prospects, "frase"].str.startswith("Ainda sem engage").all()


def test_vendedor_mediano(pontuados):
    tabela = score.por_vendedor(pontuados)
    assert len(tabela) == 27   # vendedores com deal aberto em 31/12/2017
    mediana = tabela.median()
    assert mediana[[ATACAR, FECHAR, NUTRICAO, LIMPAR, CADASTRO]].tolist() == [4, 3, 7, 9, 32]
    assert mediana["total"] == 79
    assert mediana["foco"] == 11


def test_foco_e_a_lista_hoje(pontuados):
    hoje = score.foco(pontuados)
    assert len(hoje) == 291
    assert set(hoje["rotulo"]) == set(score.FOCO)
    assert hoje["score"].is_monotonic_decreasing


def test_formatos():
    assert score.dinheiro(2133816) == "$2.133.816"
    assert score.porcento(0.479) == "48%"
    assert score.porcento(0.0012075, 2) == "0,12%"
