"""Fase 2: a curva do Clima e os estados na data de referência (31/12/2017)."""
import pytest

from lead_scorer import clima


def test_curva_corrigida(base):
    curva = clima.curva_corrigida(base.deals, base.data_ref)
    esperado = {0: 0.519, 14: 0.501, 30: 0.486, 60: 0.463, 90: 0.349, 120: 0.095}
    for idade, chance in esperado.items():
        assert curva([idade])[0] == pytest.approx(chance, abs=0.002), idade
    assert curva.maximo == 138
    assert curva([130])[0] == pytest.approx(0.05)   # piso
    assert curva([500])[0] == pytest.approx(0.05)   # sem precedente


def test_curva_do_prd_continua_reproduzivel(base):
    curva = clima.curva_prd(base.deals, base.data_ref)
    assert curva([0])[0] == pytest.approx(0.632, abs=0.002)
    assert curva([120])[0] == pytest.approx(0.756, abs=0.002)


def test_deal_velho_vale_menos_na_curva_corrigida(base):
    curva = clima.curva_corrigida(base.deals, base.data_ref)
    assert curva([120])[0] < curva([60])[0] < curva([0])[0]


def test_estados_na_referencia(base):
    retrato = clima.aplicar(base, tipo="corrigida")
    assert retrato["estado"].value_counts().to_dict() == {
        "sem precedente": 1291,
        "a qualificar": 500,
        "esfriando": 188,
        "ativo": 103,
        "novo": 7,
    }
    assert retrato["selo_esfriando"].sum() == 188
    assert retrato["chance"].between(0, 1).all()
