"""Clima do Deal: a chance de um deal aberto fechar ganho, pela idade dele.

Analogia: previsão do tempo. Olhamos o que aconteceu com deals da mesma idade
no passado para dizer a chance deste. A idade é o único sinal que se manteve
no teste temporal; os outros indicadores ficam no autoteste (validacao.py).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

import config

A_QUALIFICAR = "a qualificar"
NOVO = "novo"
ATIVO = "ativo"
ESFRIANDO = "esfriando"
SEM_PRECEDENTE = "sem precedente"
ESTADOS = (A_QUALIFICAR, NOVO, ATIVO, ESFRIANDO, SEM_PRECEDENTE)


@dataclass
class Curva:
    """Chance de fechar ganho para cada idade, de 0 até o último dia com histórico."""

    chance: np.ndarray
    ultimo_dia: int
    tipo: str
    data_corte: pd.Timestamp

    def __call__(self, idades) -> np.ndarray:
        idades = np.asarray(idades, dtype=float)
        saida = np.full(idades.shape, config.PISO_CHANCE)
        ok = ~np.isnan(idades) & (idades >= 0) & (idades <= self.ultimo_dia)
        saida[ok] = self.chance[idades[ok].astype(int)]
        return saida


def _fechados_ate(deals: pd.DataFrame, data) -> pd.Series:
    return deals["close_date"].notna() & (deals["close_date"] <= data)


def curva_corrigida(deals: pd.DataFrame, data_corte) -> Curva:
    """Aprende com todos os deals engajados até a data, inclusive os ainda abertos.

    Um deal aberto conta como "ainda sem desfecho" até a data de corte. É isso
    que impede a curva de achar que deal velho é bom: muitos nunca fecham.
    Método: incidência acumulada de ganho, com perda como risco concorrente
    (uma tábua de sobrevivência que separa quem ganhou de quem perdeu).
    """
    data_corte = pd.Timestamp(data_corte)
    d = deals[deals["engage_date"].notna() & (deals["engage_date"] <= data_corte)]
    fechou = _fechados_ate(d, data_corte).to_numpy()
    idade_hoje = (data_corte - d["engage_date"]).dt.days.to_numpy()
    dur = np.where(fechou, d["ciclo"].fillna(0).to_numpy(), idade_hoje).astype(int)
    ganhou = fechou & d["ganhou"].to_numpy()
    perdeu = fechou & ~d["ganhou"].to_numpy()

    t_max = int(dur.max())
    em_risco = np.bincount(dur, minlength=t_max + 1)[::-1].cumsum()[::-1]
    ganhos = np.bincount(dur[ganhou], minlength=t_max + 1)
    perdas = np.bincount(dur[perdeu], minlength=t_max + 1)
    taxa_ganho = np.divide(ganhos, em_risco, out=np.zeros(t_max + 1), where=em_risco > 0)
    taxa_perda = np.divide(perdas, em_risco, out=np.zeros(t_max + 1), where=em_risco > 0)

    sem_desfecho = np.cumprod(1 - taxa_ganho - taxa_perda)          # até o fim do dia t
    sem_desfecho_antes = np.concatenate([[1.0], sem_desfecho[:-1]])
    ganho_no_dia = sem_desfecho_antes * taxa_ganho
    ganho_depois = np.concatenate([np.cumsum(ganho_no_dia[::-1])[::-1][1:], [0.0]])
    chance = np.divide(ganho_depois, sem_desfecho, out=np.zeros(t_max + 1), where=sem_desfecho > 0)

    ultimo = int(np.max(np.nonzero(ganhos + perdas)[0]))
    chance = np.maximum(chance[: ultimo + 1], config.PISO_CHANCE)
    return Curva(chance, ultimo, "corrigida", data_corte)


def curva_prd(deals: pd.DataFrame, data_corte) -> Curva:
    """Versão 1 (PRD): taxa de ganho dos deals fechados com ciclo maior que a idade.

    Só olha quem fechou. Mantida para comparação: perdeu na simulação porque
    ignora os deals que nunca fecham.
    """
    data_corte = pd.Timestamp(data_corte)
    h = deals[_fechados_ate(deals, data_corte) & deals["engage_date"].notna()]
    ciclos = h["ciclo"].to_numpy()
    ganhos = h["ganhou"].to_numpy()
    ultimo = int(ciclos.max())
    chance = np.empty(ultimo + 1)
    degrau = np.nan
    for idade in range(ultimo + 1):
        acima = ciclos > idade
        if acima.sum() >= config.MIN_CASOS_CURVA_PRD:
            degrau = ganhos[acima].mean()
        chance[idade] = degrau
    return Curva(chance, ultimo, "prd", data_corte)


def construir_curva(deals: pd.DataFrame, data_corte, tipo: str | None = None) -> Curva:
    tipo = tipo or config.CURVA
    if tipo == "corrigida":
        return curva_corrigida(deals, data_corte)
    if tipo == "prd":
        return curva_prd(deals, data_corte)
    raise ValueError(f"Curva desconhecida: {tipo}")


def abertos_em(deals: pd.DataFrame, data, incluir_prospecting: bool = False) -> pd.Series:
    """Deals abertos no fim do dia `data`: engajados até ela e ainda sem desfecho."""
    data = pd.Timestamp(data)
    engajado = deals["engage_date"].notna() & (deals["engage_date"] <= data)
    sem_desfecho = deals["close_date"].isna() | (deals["close_date"] > data)
    aberto = engajado & sem_desfecho
    if incluir_prospecting:
        aberto = aberto | deals["deal_stage"].eq("Prospecting")
    return aberto


def aplicar(base, data=None, tipo: str | None = None) -> pd.DataFrame:
    """Retrato do Clima dos deals abertos numa data (padrão: data de referência).

    Prospecting ainda não tem data de engage: entra como "a qualificar", com a
    chance de quem engaja hoje (premissa explícita no PRD).
    """
    data = pd.Timestamp(data) if data is not None else base.data_ref
    curva = construir_curva(base.deals, data, tipo)
    na_referencia = data == base.data_ref
    abertos = base.deals[abertos_em(base.deals, data, incluir_prospecting=na_referencia)].copy()

    abertos["idade"] = (data - abertos["engage_date"]).dt.days
    prospect = abertos["engage_date"].isna()
    abertos["chance"] = np.where(prospect, curva([0])[0], curva(abertos["idade"].fillna(0)))
    abertos["estado"] = np.select(
        [
            prospect,
            abertos["idade"] <= config.LIMITE_NOVO,
            abertos["idade"] <= config.LIMITE_ATIVO,
            abertos["idade"] <= curva.ultimo_dia,
        ],
        [A_QUALIFICAR, NOVO, ATIVO, ESFRIANDO],
        default=SEM_PRECEDENTE,
    )
    abertos["selo_esfriando"] = abertos["estado"].eq(ESFRIANDO)
    return abertos
