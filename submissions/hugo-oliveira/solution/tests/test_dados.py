"""Fase 1: a base carregada bate com o raio-x feito antes de qualquer código."""
import pandas as pd


def test_tamanhos(base):
    assert len(base.deals) == 8800
    assert len(base.contas) == 85
    assert len(base.produtos) == 7
    assert len(base.times) == 35
    assert base.deals["sales_agent"].nunique() == 30  # 5 vendedores do cadastro não têm deals
    assert base.deals["opportunity_id"].is_unique


def test_correcoes(base):
    assert base.gtx_pro_corrigidos == 1480
    assert "GTXPro" not in set(base.deals["product"])
    assert "technolgy" not in set(base.contas["sector"])
    assert base.deals["sales_price"].notna().all()  # todo deal achou o produto


def test_abertos_e_sem_conta(base):
    assert base.deals["aberto"].sum() == 2089
    assert (base.deals["aberto"] & base.deals["sem_conta"]).sum() == 1425
    # Na base, só deal aberto fica sem conta. Por isso "sem conta" não pode
    # virar sinal de previsão: seria olhar o futuro.
    assert not (~base.deals["aberto"] & base.deals["sem_conta"]).any()


def test_data_de_referencia(base):
    assert base.data_ref == pd.Timestamp("2017-12-31")


def test_valor_do_deal_aberto_e_o_preco_de_tabela(base):
    abertos = base.deals[base.deals["aberto"]]
    assert (abertos["valor"] == abertos["sales_price"]).all()
