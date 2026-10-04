"""Clima do Deal: chance de fechar ganho pela idade e carga de pipeline.

Analogia: previsão do tempo. Olhamos o que aconteceu com deals da mesma idade
e carga de trabalho no passado para dizer a chance deste.

Sinais que resistiram ao teste temporal (autoteste em validacao.py):
- Idade: +98% de poder preditivo (tábua de sobrevivência)
- Carga de pipeline (deals abertos simultâneos): +15.7 pontos de diferença
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
    """Chance de fechar ganho para cada valor (idade ou carga), de min até max."""

    chance: np.ndarray
    maximo: int
    tipo: str
    data_corte: pd.Timestamp

    def __call__(self, valores) -> np.ndarray:
        valores = np.asarray(valores, dtype=float)
        saida = np.full(valores.shape, config.PISO_CHANCE)
        ok = ~np.isnan(valores) & (valores >= 0) & (valores <= self.maximo)
        saida[ok] = self.chance[valores[ok].astype(int)]
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
    d = deals[deals["engage_date"].notna() & (deals["engage_date"] <= data_corte)].copy()
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

    sem_desfecho = np.cumprod(1 - taxa_ganho - taxa_perda)
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


def curva_carga(deals: pd.DataFrame, data_corte) -> Curva:
    """Fator multiplicativo por carga de pipeline do vendedor.

    Carga = quantos deals o vendedor tinha abertos simultaneamente.
    Testado em autoteste (validacao.py): +15.7 pontos de diferença (baixa vs alta).
    
    Retorna fator para 3 faixas: 0=baixa, 1=média, 2=alta.
    """
    data_corte = pd.Timestamp(data_corte)
    
    # Calcular carga de pipeline para cada deal
    cargas = []
    for _, row in deals.iterrows():
        if pd.isna(row["engage_date"]) or pd.isna(row["sales_agent"]):
            cargas.append(np.nan)
            continue
        mesmo_vend = deals[deals["sales_agent"] == row["sales_agent"]]
        abertos_na_epoca = mesmo_vend[
            (mesmo_vend["engage_date"] <= row["engage_date"]) &
            ((mesmo_vend["close_date"].isna()) | (mesmo_vend["close_date"] > row["engage_date"]))
        ]
        cargas.append(len(abertos_na_epoca))
    
    d = deals.assign(_carga_temp=cargas).copy()
    d_fechados = d[_fechados_ate(d, data_corte) & d["engage_date"].notna()].copy()
    
    if len(d_fechados) == 0:
        return Curva(np.array([1.0, 1.0, 1.0]), 2, "carga", data_corte)
    
    # Tercis da carga
    carga_array = d_fechados["_carga_temp"].dropna().to_numpy()
    if len(carga_array) == 0:
        return Curva(np.array([1.0, 1.0, 1.0]), 2, "carga", data_corte)
    
    p33, p66 = np.percentile(carga_array, [33, 66])
    
    def faixa_carga(c):
        if pd.isna(c):
            return 1.0
        if c <= p33:
            return 0
        elif c <= p66:
            return 1
        else:
            return 2
    
    d_fechados.loc[:, "_faixa"] = d_fechados["_carga_temp"].apply(faixa_carga)
    
    # Taxa de ganho por faixa
    chance = np.zeros(3)
    for faixa in [0, 1, 2]:
        mask = d_fechados["_faixa"] == faixa
        if mask.sum() > 0:
            chance[faixa] = d_fechados.loc[mask, "ganhou"].mean()
        else:
            chance[faixa] = config.PISO_CHANCE
    
    # Normalizar para fator (vs média geral)
    media_geral = d_fechados["ganhou"].mean()
    if media_geral > 0:
        fator = chance / media_geral
    else:
        fator = np.ones(3)
    
    fator = np.maximum(fator, config.PISO_CHANCE)
    return Curva(fator, 2, "carga", data_corte)


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

    Retorna CHANCE_FINAL = CHANCE_BASE(idade) × FATOR_CARGA(carga_pipeline)
    Prospecting ainda não tem data de engage: entra como "a qualificar".
    """
    data = pd.Timestamp(data) if data is not None else base.data_ref
    curva = construir_curva(base.deals, data, tipo)
    curva_carga_obj = curva_carga(base.deals, data)
    na_referencia = data == base.data_ref
    abertos = base.deals[abertos_em(base.deals, data, incluir_prospecting=na_referencia)].copy()

    # Calcular carga de pipeline para cada deal
    cargas = []
    for _, row in abertos.iterrows():
        if pd.isna(row["engage_date"]) or pd.isna(row["sales_agent"]):
            cargas.append(np.nan)
            continue
        mesmo_vend = base.deals[base.deals["sales_agent"] == row["sales_agent"]]
        abertos_na_epoca = mesmo_vend[
            (mesmo_vend["engage_date"] <= row["engage_date"]) &
            ((mesmo_vend["close_date"].isna()) | (mesmo_vend["close_date"] > row["engage_date"]))
        ]
        cargas.append(len(abertos_na_epoca))
    
    abertos.loc[:, "carga_pipeline"] = cargas

    # Idade e chance_base
    abertos.loc[:, "idade"] = (data - abertos["engage_date"]).dt.days
    prospect = abertos["engage_date"].isna()
    abertos.loc[:, "chance_base"] = np.where(prospect, curva([0])[0], curva(abertos["idade"].fillna(0)))
    
    # Carga e fator_carga
    def faixa_carga(c):
        if pd.isna(c):
            return 1.0
        all_cargas = abertos["carga_pipeline"].dropna().to_numpy()
        if len(all_cargas) == 0:
            return 1.0
        p33, p66 = np.percentile(all_cargas, [33, 66])
        if c <= p33:
            return 0.0
        elif c <= p66:
            return 1.0
        else:
            return 2.0
    
    abertos.loc[:, "faixa_carga"] = abertos["carga_pipeline"].apply(faixa_carga)
    abertos.loc[:, "fator_carga"] = curva_carga_obj(abertos["faixa_carga"])
    
    # Chance final
    abertos.loc[:, "chance"] = (abertos["chance_base"] * abertos["fator_carga"]).clip(config.PISO_CHANCE, 1.0)
    
    # Estado por idade
    abertos.loc[:, "estado"] = np.select(
        [
            prospect,
            abertos["idade"] <= config.LIMITE_NOVO,
            abertos["idade"] <= config.LIMITE_ATIVO,
            abertos["idade"] <= curva.maximo,
        ],
        [A_QUALIFICAR, NOVO, ATIVO, ESFRIANDO],
        default=SEM_PRECEDENTE,
    )
    abertos.loc[:, "selo_esfriando"] = abertos["estado"].eq(ESFRIANDO)
    return abertos
