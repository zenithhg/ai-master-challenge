"""Carga e limpeza da base: 4 CSVs do Kaggle (CRM Sales Opportunities, CC0)."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import config

CORRECAO_PRODUTO = {"GTXPro": "GTX Pro"}        # grafia diferente da tabela de produtos
CORRECAO_SETOR = {"technolgy": "technology"}    # erro de digitação na base
ESTAGIOS_ABERTOS = ("Prospecting", "Engaging")


@dataclass
class Base:
    """A base pronta para uso: um deal por linha, já com produto, time e conta."""

    deals: pd.DataFrame
    contas: pd.DataFrame
    produtos: pd.DataFrame
    times: pd.DataFrame
    data_ref: pd.Timestamp
    gtx_pro_corrigidos: int


def carregar(pasta=None) -> Base:
    """Lê os 4 CSVs, corrige os dois erros conhecidos e junta tudo por deal."""
    pasta = Path(pasta) if pasta else config.PASTA_DADOS
    contas = pd.read_csv(pasta / "accounts.csv")
    produtos = pd.read_csv(pasta / "products.csv")
    times = pd.read_csv(pasta / "sales_teams.csv")
    deals = pd.read_csv(pasta / "sales_pipeline.csv", parse_dates=["engage_date", "close_date"])

    gtx_pro = int(deals["product"].isin(list(CORRECAO_PRODUTO)).sum())
    deals["product"] = deals["product"].replace(CORRECAO_PRODUTO)
    contas["sector"] = contas["sector"].replace(CORRECAO_SETOR)

    deals = (
        deals.merge(produtos, on="product", how="left", validate="many_to_one")
        .merge(times, on="sales_agent", how="left", validate="many_to_one")
        .merge(contas, on="account", how="left", validate="many_to_one")
    )
    deals["aberto"] = deals["deal_stage"].isin(ESTAGIOS_ABERTOS)
    deals["ganhou"] = deals["deal_stage"].eq("Won")
    deals["sem_conta"] = deals["account"].isna()
    # Valor do deal: preço de tabela se está aberto; valor fechado se já fechou.
    deals["valor"] = np.where(deals["aberto"], deals["sales_price"], deals["close_value"])
    deals["ciclo"] = (deals["close_date"] - deals["engage_date"]).dt.days

    if config.DATA_REFERENCIA:
        data_ref = pd.Timestamp(config.DATA_REFERENCIA)
    else:
        data_ref = deals["close_date"].max()
    return Base(deals, contas, produtos, times, data_ref, gtx_pro)
