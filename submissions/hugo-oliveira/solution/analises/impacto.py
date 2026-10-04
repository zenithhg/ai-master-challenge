"""Impacto estimado da lista por mês e por ano: receita a mais e horas poupadas.

Rodar dentro de solution/:  python analises/impacto.py

É equivalência, não medição (mesma premissa de validacao.equivalencia_por_hora):
- Receita: o ganho da simulação das segundas contra o feeling (sorteio), com a
  chance que o app usa (idade + carga), aplicado à receita média mensal de 2017.
- Horas: a semana de 40 horas dividida entre os 5 deals da semana; a diferença
  de horas em deal que nunca fecha, medida em 16 semanas, estendida para 52.
A prova de causa é o piloto recomendado no README.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import fator_carga as fc
from lead_scorer import validacao as v

SEMANAS_NO_ANO = 52


def impacto() -> dict:
    """Ganho contra o feeling, receita a mais por vendedor por mês e horas poupadas por semana."""
    produtividade = v.resumo_produtividade(fc.base)
    v.retratos_das_segundas = fc.retratos_com_carga
    try:
        resumo = v.simular_segundas(fc.base).resumo
    finally:
        v.retratos_das_segundas = fc.retratos_originais
    ganho = resumo.loc["clima_prd", "vs_feeling"]
    return {
        "vendedores": produtividade["vendedores"],
        "receita_mes_base": produtividade["receita_por_mes_media"],
        "ganho_vs_feeling": ganho,
        "receita_mes_vendedor": produtividade["receita_por_mes_media"] * ganho,
        "horas_semana_vendedor": resumo.loc["sorteio", "horas_semana_deal_morto"]
        - resumo.loc["clima_prd", "horas_semana_deal_morto"],
    }


if __name__ == "__main__":
    i = impacto()
    n, receita, horas = i["vendedores"], i["receita_mes_vendedor"], i["horas_semana_vendedor"]
    semanas_mes = SEMANAS_NO_ANO / 12
    print(f"Ganho da lista contra o feeling: {100 * i['ganho_vs_feeling']:+.1f}% "
          f"sobre a receita média de ${i['receita_mes_base']:,.0f} por vendedor por mês\n")
    print(f"{'':40}{'por vendedor':>14}{f'time ({n})':>14}")
    print(f"{'Receita a mais por mês ($)':40}{receita:>14,.0f}{receita * n:>14,.0f}")
    print(f"{'Receita a mais por ano ($)':40}{receita * 12:>14,.0f}{receita * 12 * n:>14,.0f}")
    print(f"{'Horas a menos em deal morto, por mês':40}{horas * semanas_mes:>14.1f}{horas * semanas_mes * n:>14,.0f}")
    print(f"{'Horas a menos em deal morto, por ano':40}{horas * SEMANAS_NO_ANO:>14.0f}"
          f"{horas * SEMANAS_NO_ANO * n:>14,.0f}")
    print(f"\nPor ano: {horas * SEMANAS_NO_ANO / config.HORAS_POR_DIA:.1f} dias úteis por vendedor; "
          f"{horas * SEMANAS_NO_ANO * n / (SEMANAS_NO_ANO * config.HORAS_POR_SEMANA):.1f} "
          "vendedores em tempo integral no time.")
