"""App do Lead Scorer: tela do vendedor (Missão do dia, Raio X e Playbook).

Rodar: streamlit run app.py (dentro da pasta solution/).
Visão de gerente fica fora do escopo desta entrega (ver README).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from lead_scorer import dados, score
from lead_scorer import raio_x as rx
from lead_scorer.score import (
    ATACAR, FECHAR, QUALIFICAR, NUTRICAO, LIMPAR, CADASTRO, ROTULOS,
    dinheiro, porcento,
)

st.set_page_config(
    page_title="Lead Scorer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Linguagem simples e cor por rótulo (não muda o nome do rótulo em si) ──────

SUBTITULO = {
    ATACAR: "Vale bastante e ainda está no prazo de fechar: ligue primeiro",
    FECHAR: "Vale menos e ainda está no prazo: feche com esforço mínimo",
    QUALIFICAR: "Ainda não sabemos se vale a pena: descubra em até 2 semanas",
    NUTRICAO: "Vale muito, mas passou do prazo normal de fechamento: mantenha contato",
    LIMPAR: "Vale pouco e já esfriou: não gaste tempo aqui",
    CADASTRO: "Falta o cadastro da empresa: complete ou descarte",
}

# Verde e azul para as ações de foco; vermelho fica reservado para alerta.
EMOJI = {
    ATACAR: "🟢", FECHAR: "🔵", QUALIFICAR: "🟡",
    NUTRICAO: "🟣", LIMPAR: "⚪", CADASTRO: "⚫",
}

ABERTO_POR_PADRAO = {ATACAR, FECHAR}


def inteiro(n) -> str:
    """Número inteiro no formato brasileiro: 2089 -> "2.089"."""
    return f"{int(n):,}".replace(",", ".")


def decimal(x, casas: int = 1) -> str:
    """Decimal no formato brasileiro: 1223.6 -> "1.223,6"."""
    return f"{x:,.{casas}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def sem_formula(texto: str) -> str:
    """Escapa o $: dois valores em dólar no mesmo texto viram fórmula no Streamlit."""
    return texto.replace("$", "\\$")


# ─── Cache ────────────────────────────────────────────────────────────────────


@st.cache_resource
def _base():
    return dados.carregar()


@st.cache_data
def _pontuados():
    return score.pontuar(_base())


@st.cache_data
def _produto_do_porte():
    return rx.produto_do_porte(_base())


base = _base()
pontuados = _pontuados()

# ─── Navegação (lista ↔ detalhe) ────────────────────────────────────────────────

if "view" not in st.session_state:
    st.session_state.view = "lista"
if "deal_id" not in st.session_state:
    st.session_state.deal_id = None


def ir_para_detalhe(opportunity_id: str) -> None:
    st.session_state.view = "detalhe"
    st.session_state.deal_id = opportunity_id


def voltar_para_lista() -> None:
    st.session_state.view = "lista"
    st.session_state.deal_id = None


# ─── Sidebar: só a troca de vendedor ────────────────────────────────────────────

vendedores = sorted(pontuados["sales_agent"].dropna().unique().tolist())
# Abre no vendedor com mais negócios em foco: a primeira tela já mostra a ferramenta em uso.
em_foco = pontuados.loc[pontuados["rotulo"].isin(score.FOCO), "sales_agent"].value_counts()
padrao = vendedores.index(em_foco.idxmax()) if not em_foco.empty else 0

with st.sidebar:
    st.title("🎯 Lead Scorer")
    vendedor = st.selectbox("Ver como vendedor", vendedores, index=padrao)
    st.caption(f"Referência: {base.data_ref.strftime('%d/%m/%Y')}")
    st.caption(f"Deals abertos (todo o time): {inteiro(len(pontuados))}")

meus = pontuados[pontuados["sales_agent"] == vendedor]


# ─── Tela 1: Missão do dia (lista) ───────────────────────────────────────────────


def tela_lista() -> None:
    st.header("🎯 Missão do dia")
    st.caption(
        f"Negócios abertos de {vendedor}, do maior Score para o menor. "
        "Clique em \"Ver\" para abrir o Raio X e o Playbook do negócio."
    )

    foco_vendedor = meus[meus["rotulo"].isin(score.FOCO)]
    c1, c2, c3 = st.columns(3)
    c1.metric("Negócios em foco", len(foco_vendedor))
    c2.metric("Valor em jogo", dinheiro(foco_vendedor["valor"].sum()))
    c3.metric("Valor esperado", dinheiro(foco_vendedor["valor_esperado"].sum()))

    st.divider()

    if meus.empty:
        st.info("Nenhum negócio aberto para este vendedor.")
        return

    for rotulo in ROTULOS:
        grupo = meus[meus["rotulo"] == rotulo]
        if grupo.empty:
            continue

        titulo = (
            f"{EMOJI[rotulo]} {rotulo} ({len(grupo)}) · {SUBTITULO[rotulo]}"
        )
        with st.expander(titulo, expanded=(rotulo in ABERTO_POR_PADRAO)):
            st.caption(f"Valor total do grupo: {dinheiro(grupo['valor'].sum())}")

            mostrar = grupo.head(50)
            for _, row in mostrar.iterrows():
                conta = str(row["account"]) if pd.notna(row["account"]) else "(sem conta)"
                selos = ""
                if row["selo_esfriando"]:
                    selos += " 🌡️"
                if row["selo_sem_cadastro"]:
                    selos += " ⚠️"

                col_score, col_conta, col_chance, col_valor, col_acao = st.columns(
                    [1, 4, 2, 2, 1.4]
                )
                col_score.markdown(f"Score  \n**{row['score']}**")
                col_conta.markdown(f"**{conta}{selos}**  \n{row['product']}")
                col_chance.markdown(f"Chance: {porcento(row['chance'])}")
                col_valor.markdown(f"Vale: {dinheiro(row['valor'])}")
                if col_acao.button("Ver →", key=f"ver_{row['opportunity_id']}"):
                    ir_para_detalhe(row["opportunity_id"])
                    st.rerun()
                st.divider()

            if len(grupo) > 50:
                st.caption(f"+ {len(grupo) - 50} negócios além destes 50.")


# ─── Tela 2: Detalhe do lead (Raio X + Playbook) ────────────────────────────────


def tela_detalhe(opportunity_id: str) -> None:
    if st.button("← Voltar para minha lista"):
        voltar_para_lista()
        st.rerun()

    linha = pontuados[pontuados["opportunity_id"] == opportunity_id]
    if linha.empty:
        st.warning("Esse negócio não está mais na lista de abertos.")
        return
    row = linha.iloc[0]
    conta = str(row["account"]) if pd.notna(row["account"]) else "(sem conta)"

    badges = [row["rotulo"]]
    if row["selo_esfriando"]:
        badges.append("🌡️ Esfriando")
    if row["selo_sem_cadastro"]:
        badges.append("⚠️ Sem cadastro")

    st.subheader(f"Score {row['score']} · {conta}")
    st.caption(" · ".join(badges))
    st.write(sem_formula(
        f"{row['product']} · Vendedor {row['sales_agent']} · "
        f"{porcento(row['chance'])} de chance · Vale {dinheiro(row['valor'])} · "
        f"Valor esperado {dinheiro(row['valor_esperado'])}"
    ))
    st.info(sem_formula(row["frase"]))

    raio = None
    if not row["selo_sem_cadastro"]:
        do_porte = _produto_do_porte()
        try:
            raio = rx.raio_x(base, opportunity_id, do_porte)
        except KeyError as e:
            st.error(f"Não foi possível carregar o Raio X: {e}")

    tab_raiox, tab_playbook = st.tabs(["🔍 Raio X", "📘 Playbook"])


    with tab_raiox:
        n_abertos = len(pontuados)
        st.markdown(f"#### Por que esse Score é {row['score']}?")
        st.caption(
            f"{row['score']} = o valor esperado deste negócio é maior que o de "
            f"{row['score']}% dos {inteiro(n_abertos)} negócios abertos hoje."
        )
        c1, c2 = st.columns(2)
        c1.metric("Chance de fechar", porcento(row["chance"]))
        c2.metric("Valor esperado", dinheiro(row["valor_esperado"]))
        st.caption(
            "Chance de fechar vem de negócios parecidos no passado (mesma idade e "
            "mesma carga de trabalho do vendedor na época). Valor esperado = chance × valor."
        )
        st.caption(
            "Analogia: o Score funciona como a posição numa fila de atendimento. "
            "Quanto mais perto de 100, mais na frente."
        )

        st.divider()

        if row["selo_sem_cadastro"]:
            st.warning(
                "⚠️ **Sem cadastro:** este negócio não tem conta vinculada, por isso "
                "não existe Raio X completo nem matemática do 1%.\n\n"
                "**Dica para reverter:** peça CNPJ e nome da empresa na próxima "
                "conversa e cadastre em até 7 dias, antes de investir mais tempo nele."
            )
        if row["selo_esfriando"]:
            st.warning(
                "🌡️ **Esfriando:** última tentativa esta semana. Depois de 138 "
                "dias, nenhuma venda da história fechou.\n\n"
                "**Dica para reverter:** ligue hoje com algo novo: uma notícia "
                "da empresa, um case, um convite. Não mande só \"retomando o contato\"."
            )
        if not row["selo_sem_cadastro"]:
            if raio and raio.aviso:
                st.warning(f"⚠️ {raio.aviso}")

            elif raio:
                f = raio.ficha
                st.markdown("#### Detalhe do cliente")

                aprov = porcento(f.aproveitamento) if not np.isnan(f.aproveitamento) else "sem histórico"
                delta_aprov = (
                    f"{(f.aproveitamento - f.media_do_time) * 100:+.0f} pp vs. time"
                    if not np.isnan(f.aproveitamento) else None
                )
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Negociações", f.negociacoes)
                c2.metric("Vitórias / Derrotas", f"{f.vitorias} / {f.derrotas}")
                c3.metric("Aproveitamento", aprov, delta=delta_aprov)
                c4.metric("Média do time", porcento(f.media_do_time))

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Setor:** {f.setor}")
                    st.markdown(f"**Porte:** {f.porte}")
                    st.markdown(f"**Faturamento:** ${decimal(f.receita_milhoes)} milhões/ano")
                    st.markdown(f"**Funcionários:** {inteiro(f.funcionarios)}")
                    st.markdown(f"**Sede:** {f.sede}")
                with col2:
                    if f.ultimos_5:
                        resultados = " ".join(
                            "🟢 V" if r == "V" else "🔴 D" for r in f.ultimos_5
                        )
                        st.markdown(f"**Últimos 5 resultados:** {resultados}")
                    if f.produto_mais_comprado:
                        st.markdown(f"**Produto mais comprado:** {f.produto_mais_comprado}")
                    if not np.isnan(f.ticket_medio):
                        st.markdown(f"**Ticket médio do cliente:** {dinheiro(f.ticket_medio)}")
                    if f.dias_desde_ultima_compra is not None:
                        st.markdown(f"**Última compra:** há {f.dias_desde_ultima_compra} dias")
                    if f.vendedores:
                        st.markdown(f"**Já atendido por:** {', '.join(f.vendedores)}")

                if raio.mix_do_porte is not None:
                    st.divider()
                    st.markdown(f"#### O que contas do porte \"{f.porte}\" costumam comprar")
                    mix = raio.mix_do_porte.sort_values(ascending=False)
                    mix_df = pd.DataFrame(
                        {
                            "Produto": mix.index,
                            "% das vitórias": (mix.values * 100).round(1),
                        }
                    )
                    st.dataframe(mix_df, hide_index=True)
                    if raio.ticket_do_porte:
                        st.caption(f"Ticket médio do porte: {dinheiro(raio.ticket_do_porte)}")

                if raio.frase_1pct:
                    st.divider()
                    st.markdown("#### 💰 O preço cabe no bolso?")
                    st.info(raio.frase_1pct)


    with tab_playbook:
        st.caption(
            "Genérico v1 · por regra: não usa dado comportamental do lead "
            "(veja a nota no fim)."
        )

        st.markdown("##### 💬 Abertura sugerida")
        if row["selo_sem_cadastro"]:
            st.write(
                "Sem conta cadastrada, não dá para personalizar pelo histórico. "
                "Pergunte o CNPJ antes de tudo."
            )
        elif raio and raio.ficha.negociacoes > 1:
            f = raio.ficha
            produto_txt = (
                f" e já comprou {f.produto_mais_comprado} antes" if f.produto_mais_comprado else ""
            )
            st.info(
                f"Esta conta já negociou {f.negociacoes} vezes{produto_txt}. "
                f"Puxe esse histórico em vez de \"oi, tudo bem\"."
            )
        else:
            st.info(
                "Primeira negociação com esta conta. Pesquise a empresa antes de "
                "ligar: uma notícia recente vale mais que \"oi, tudo bem\"."
            )

        st.markdown("##### 🩺 Consulta médica: 3 perguntas obrigatórias")
        st.markdown(
            "1. Quais são os 3 maiores desafios de gestão hoje?  \n"
            "2. Há quanto tempo essas dores persistem?  \n"
            "3. O que você já tentou contratar antes que não funcionou?"
        )
        st.caption(
            "A resposta da pergunta 3 vira a contraobjeção: curso anterior → "
            "venda acompanhamento; consultoria anterior → venda capacitação da equipe."
        )


        if raio and raio.frase_1pct:
            st.markdown("##### 💰 Matemática do 1%")
            st.info(raio.frase_1pct)

        st.markdown("##### 🛡️ Contraobjeção")
        if row["selo_esfriando"]:
            st.write(
                "Negócio parado há tempo. Não insista no mesmo discurso: pergunte "
                "o que mudou desde a última conversa antes de oferecer qualquer coisa."
            )
        elif row["selo_sem_cadastro"]:
            st.write(
                "Sem CNPJ não tem como avançar a proposta. Trate isso como pré-"
                "requisito, não como detalhe."
            )
        else:
            st.write(
                "\"Vou pensar\" → pergunte o que especificamente precisa pensar. "
                "\"Está caro\" → volte para a matemática do 1% acima."
            )

        st.divider()
        st.caption(
            "🔧 Melhoria futura sugerida: a metodologia do Alfredo usa sinais "
            "comportamentais (engajamento social, conteúdo consumido, nível de "
            "consciência do lead) que não existem neste dataset. Com esses dados, "
            "o score preditivo poderia incorporar uma dimensão de \"prontidão\" "
            "além de tempo e carga de pipeline."
        )


if st.session_state.view == "detalhe" and st.session_state.deal_id:
    tela_detalhe(st.session_state.deal_id)
else:
    tela_lista()
