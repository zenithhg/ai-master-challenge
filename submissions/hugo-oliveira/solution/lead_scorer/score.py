"""Score (0 a 100), rótulo de ação e a frase para o vendedor.

Analogia: a triagem de um pronto-socorro. O Clima mede a gravidade de cada
deal, o rótulo diz para qual sala ele vai e o Score ordena a fila.
"""
import numpy as np
import pandas as pd

import config
from lead_scorer import clima

ATACAR = "Atacar agora"
FECHAR = "Fechar rápido"
QUALIFICAR = "Qualificar em 14 dias"
NUTRICAO = "Nutrição de elite"
LIMPAR = "Limpar ou automação"
CADASTRO = "Completar cadastro ou limpar"
ROTULOS = (ATACAR, FECHAR, QUALIFICAR, NUTRICAO, LIMPAR, CADASTRO)
FOCO = (ATACAR, FECHAR)  # a lista "Hoje" do vendedor

O_QUE_FAZER = {
    ATACAR: "Consulta médica e proposta.",
    FECHAR: "Feche com esforço mínimo.",
    QUALIFICAR: "Consulta médica em até 14 dias.",
    NUTRICAO: "Régua de 90 dias com você.",
    LIMPAR: "Régua automática ou feche como Lost.",
    CADASTRO: "Complete o cadastro em 7 dias ou feche.",
}

SELO_ESFRIANDO = "Esfriando: última tentativa esta semana"
SELO_SEM_CADASTRO = "Sem cadastro"

COLUNAS = [
    "opportunity_id", "sales_agent", "manager", "regional_office", "account",
    "product", "deal_stage", "engage_date", "idade", "estado", "chance", "valor",
    "valor_esperado", "score", "rotulo", "selo_esfriando", "selo_sem_cadastro", "frase",
]


def dinheiro(valor) -> str:
    """$4.821: ponto separa os milhares, como no PRD."""
    return f"${valor:,.0f}".replace(",", ".")


def porcento(fracao, casas: int = 0) -> str:
    """0,479 vira 48%; com casas=2, 0,0012 vira 0,12%."""
    return f"{fracao * 100:.{casas}f}%".replace(".", ",")


def _ha(idade) -> str:
    idade = int(idade)
    if idade == 0:
        return "hoje"
    return "há 1 dia" if idade == 1 else f"há {idade} dias"


def rotular(deals: pd.DataFrame) -> np.ndarray:
    """Rótulo de ação pelo estado do Clima, valor do produto e cadastro (PRD 5.4)."""
    sem_precedente = deals["estado"].eq(clima.SEM_PRECEDENTE)
    qualificar = deals["estado"].isin([clima.A_QUALIFICAR, clima.NOVO])
    valor_alto = deals["sales_price"] >= config.VALOR_ALTO
    return np.select(
        [
            sem_precedente & deals["sem_conta"],
            sem_precedente & valor_alto,
            sem_precedente,
            qualificar,
            valor_alto,
        ],
        [CADASTRO, NUTRICAO, LIMPAR, QUALIFICAR, ATACAR],
        default=FECHAR,
    )


def _score(valor_esperado: pd.Series) -> pd.Series:
    """Score 90 = valor esperado maior que o de 90% dos deals abertos."""
    abaixo = valor_esperado.rank(method="min") - 1
    return np.floor(100 * abaixo / len(valor_esperado)).astype(int)


def frase(estado: str, idade, chance: float, valor: float, rotulo: str) -> str:
    """O porquê do número em frase de vendedor, seguido do que fazer."""
    if estado == clima.A_QUALIFICAR:
        porque = f"Ainda sem engage. Deals que engajam terminam ganhos {porcento(chance)} das vezes."
    elif estado == clima.SEM_PRECEDENTE:
        porque = (
            f"Aberto {_ha(idade)}, mais que qualquer venda já fechada. "
            f"Chance estimada: {porcento(chance)} (piso)."
        )
    else:
        porque = (
            f"Deals como este, abertos {_ha(idade)}, terminaram ganhos "
            f"{porcento(chance)} das vezes."
        )
    return (
        f"{porque} Vale {dinheiro(valor)}. Valor esperado: {dinheiro(valor * chance)}. "
        f"{O_QUE_FAZER[rotulo]}"
    )


def pontuar(base, data=None) -> pd.DataFrame:
    """Deals abertos numa data (padrão: data de referência), do maior Score para o menor."""
    df = clima.aplicar(base, data)
    df["valor_esperado"] = df["chance"] * df["valor"]
    df["score"] = _score(df["valor_esperado"])
    df["rotulo"] = rotular(df)
    df["selo_sem_cadastro"] = df["sem_conta"]
    df["frase"] = [
        frase(e, i, c, v, r)
        for e, i, c, v, r in zip(df["estado"], df["idade"], df["chance"], df["valor"], df["rotulo"])
    ]
    df = df.sort_values(["score", "opportunity_id"], ascending=[False, True])
    return df[COLUNAS].reset_index(drop=True)


def foco(pontuados: pd.DataFrame) -> pd.DataFrame:
    """A lista "Hoje": Atacar agora e Fechar rápido, do maior Score para o menor."""
    hoje = pontuados[pontuados["rotulo"].isin(FOCO)]
    return hoje.sort_values(["score", "opportunity_id"], ascending=[False, True])


def distribuicao(pontuados: pd.DataFrame) -> pd.DataFrame:
    """Quantos deals e quanto valor em cada rótulo, na ordem de ação."""
    tabela = pontuados.groupby("rotulo")["valor"].agg(deals="size", valor="sum")
    return tabela.reindex(list(ROTULOS), fill_value=0)


def por_vendedor(pontuados: pd.DataFrame) -> pd.DataFrame:
    """Deals de cada rótulo por vendedor, mais o total e o foco."""
    tabela = pd.crosstab(pontuados["sales_agent"], pontuados["rotulo"])
    tabela = tabela.reindex(columns=list(ROTULOS), fill_value=0)
    tabela["total"] = tabela[list(ROTULOS)].sum(axis=1)
    tabela["foco"] = tabela[list(FOCO)].sum(axis=1)
    return tabela


if __name__ == "__main__":
    from lead_scorer import dados

    pontuados = pontuar(dados.carregar())
    print(distribuicao(pontuados).to_string())
    print(f"\nSelo esfriando: {int(pontuados['selo_esfriando'].sum())}")
    print(f"Vendedor mediano:\n{por_vendedor(pontuados).median().to_string()}")
