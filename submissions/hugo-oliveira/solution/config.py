"""Parâmetros do Lead Scorer.

Tudo o que é premissa fica aqui, com o motivo ao lado, para ser mudado sem
mexer na lógica.
"""
from pathlib import Path

# Onde estão os 4 CSVs do Kaggle (licença CC0), conferidos por assinatura.
PASTA_DADOS = Path(__file__).resolve().parent / "data"

# Data de referência: a última data de fechamento da base (31/12/2017).
# Nunca a data de hoje: a base é histórica. None = usar a maior close_date.
DATA_REFERENCIA = None

# Curva de chance do Clima do Deal.
# "corrigida": aprende com todos os deals, inclusive os que continuam abertos
#   e podem nunca fechar. Venceu na simulação das segundas.
# "prd": versão 1, aprende só com deals fechados. Fica para comparação.
CURVA = "corrigida"
MIN_CASOS_CURVA_PRD = 100  # a versão 1 só usava degraus com 100 casos ou mais

# Piso de chance para deal sem precedente (mais velho que qualquer venda da
# história). Premissa: a pesquisa Win/Lost vai medir a taxa real.
PISO_CHANCE = 0.05

# Estados do Clima, pela idade do deal (dias desde o engage).
LIMITE_NOVO = 14   # 0 a 14 dias: novo, hora de qualificar
LIMITE_ATIVO = 90  # 15 a 90 dias: ativo
# De 91 dias até o maior ciclo da história: esfriando (selo de alerta).
# Acima disso: sem precedente.

# Simulação das segundas (validação do Clima).
SIM_INICIO = "2017-05-01"
SIM_FIM = "2017-08-14"       # última segunda com 138 dias para fechar até 31/12
SIM_DEALS_POR_SEMANA = 5     # o time fechou 5,1 deals por vendedor por semana
SIM_RODADAS_SORTEIO = 300    # repetições do sorteio (o feeling sem informação)
SIM_SEMENTE = 7

# Autoteste dos indicadores: aprende com o que fechou antes do corte e testa
# nos deals que engajaram depois dele.
AUTOTESTE_CORTE = "2017-07-01"
AUTOTESTE_FIM = "2017-08-14"
AUTOTESTE_MIN_CASOS = 200
AUTOTESTE_LIMIAR = 0.05        # liga com 5 pontos de diferença ou mais
AUTOTESTE_OBSERVACAO = 0.02    # de 2 a 5 pontos: em observação

# Produtividade por hora (premissa: 8 horas por dia útil, sem feriados).
HORAS_POR_DIA = 8
HORAS_POR_SEMANA = 40
