"""Fase 2: validação. Os números aqui são os que vão para o README e o pitch."""
import pytest

from lead_scorer import validacao


@pytest.fixture(scope="module")
def simulacao(base):
    return validacao.simular_segundas(base)


def test_tamanho_da_simulacao(simulacao):
    assert len(simulacao.segundas) == 16
    assert len(simulacao.vendedores) == 30


def test_clima_acerta_mais_e_perde_menos_tempo(simulacao):
    r = simulacao.resumo
    assert r.loc["clima", "acerto_semanas"] == pytest.approx(0.482, abs=0.003)
    assert r.loc["clima", "tempo_nunca_fecha"] == pytest.approx(0.307, abs=0.003)
    assert r.loc["maior_valor", "tempo_nunca_fecha"] == pytest.approx(0.405, abs=0.003)
    assert r.loc["clima", "tempo_nunca_fecha"] < r.loc["sorteio", "tempo_nunca_fecha"]


def test_clima_rende_mais(simulacao):
    r = simulacao.resumo
    assert r.loc["clima", "vs_maior_valor"] == pytest.approx(0.525, abs=0.01)
    assert 0 < r.loc["clima", "vs_feeling"] < 0.15
    assert r.loc["clima", "receita"] > r.loc["clima_prd", "receita"] > r.loc["maior_valor", "receita"]
    # O feeling trabalha mais que o dobro de deals para chegar perto.
    assert r.loc["sorteio", "deals"] > 2 * r.loc["clima", "deals"]


def test_vendedor_a_vendedor(simulacao):
    v = simulacao.vendedor_a_vendedor.set_index("contra")
    assert v.loc["Sem Clima: maior valor", "vendedores_em_que_o_clima_ganha"] == 26
    assert v.loc["Sem Clima: feeling (sorteio)", "vendedores_em_que_o_clima_ganha"] >= 15


def test_nota_de_ordenacao(simulacao):
    notas = validacao.nota_ordenacao(simulacao.retratos)
    assert notas["corrigida"] == pytest.approx(0.652, abs=0.005)
    assert notas["prd"] == pytest.approx(0.533, abs=0.005)


def test_calibracao_mostra_o_erro_da_versao_1(simulacao):
    c = validacao.calibracao(simulacao.retratos).loc["91-138"]
    assert c["ganhou_de_fato"] < 0.25      # deal de 91 a 138 dias quase não ganha
    assert c["chance_prd"] > 0.70          # a versão 1 dizia que era o melhor
    assert c["chance_corrigida"] < 0.40    # a corrigida acompanha a realidade


def test_autoteste(base):
    a = validacao.autoteste(base)
    assert set(a.index) == set(validacao.INDICADORES)
    assert a.loc["relacionamento", "status"] != "ligado"
    for perfil in ("setor", "porte", "funcionarios", "sede"):
        assert a.loc[perfil, "status"] == "desligado", perfil
    # Região e gerente são iguais para todos os deals de um vendedor:
    # mesmo que liguem, não mudam a lista dele.
    assert not a.loc[["regiao", "gerente"], "uso_sugerido"].eq("candidato ao Score (Hugo decide)").any()


def test_produtividade(base):
    p = validacao.resumo_produtividade(base)
    assert p["vendedores"] == 30
    assert p["fechados_por_semana"] == pytest.approx(5.13, abs=0.01)
    assert p["receita_por_mes_media"] == pytest.approx(33352, abs=1)
    assert p["receita_por_hora_media"] == pytest.approx(191.24, abs=0.05)
