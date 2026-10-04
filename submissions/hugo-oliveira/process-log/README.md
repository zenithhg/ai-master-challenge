# Process Log: Hugo Oliveira

Uma entrada por sessão: data, ferramenta, o que pedi, o que a IA entregou, o que corrigi e por quê. Os erros da IA estão numerados em sequência ao longo das sessões.

## 29/09/2026: Sessão 1, leitura e escolha do desafio

- **Ferramenta:** Claude (chat)
- **O que fiz:** li a vaga, o guia de submissão e o README do challenge 003.
- **Decisão:** escolhi o 003 porque trabalho há anos como KAM B2B priorizando carteira de oportunidades. O problema dos 35 vendedores é o meu dia a dia.
- **Próximo:** abrir os 4 CSVs e escrever hipóteses de vendedor antes de pedir qualquer código à IA.

## 29/09 a 01/10/2026: Sessão 2, descoberta, tese e desenho

- **Ferramenta:** Claude (chat com acesso aos CSVs, ao Notion e ao Todoist).
- **O que pedi:** cronograma no Todoist; raio-x dos 4 CSVs; testar minha tese de vendedor (usar os deals que já fecharam para prever os abertos, que virou o "Clima do Deal"); cruzar com a metodologia de vendas do Alfredo Soares (Raio X do lead, consulta médica, régua de nutrição, matemática do 1%); PRD e plano de desenvolvimento em fases.
- **Onde a IA errou:**
  1. Executou tarefas sem pedir aprovação. Travei e defini a regra que valeu até o fim: a IA propõe, eu aprovo.
  2. Superestimou o sinal de relacionamento (60% para 70%). Na checagem por semestre, o sinal inverteu.
  3. Bug na ordem das condições da regra dos rótulos. Corrigido ao conferir os números.
  4. O primeiro cenário financeiro ignorou o ticket de cada grupo (+$113 mil por mês). Refeito com o ticket real (+$92 mil por mês) e depois retirado do PRD (ver sessão 3).
- **O que decidi:**
  - Case 003, pelo encaixe com a minha experiência de KAM B2B e com uma ferramenta de score que já construí.
  - Nome do indicador: Clima do Deal. Na v1, usa só o tempo, o único sinal comprovado; qualquer sinal novo precisa passar num autoteste.
  - Não cruzar com as bases dos outros desafios: seria inventar dado.
  - Desenho: Score + Clima do Deal + Raio X do Cliente (`docs/PRD.md`).
- **Achado:** o perfil do cliente (setor, porte, sede, histórico da conta) não separa ganho de perda. O tempo separa.

## 01/10 (noite) a 02/10/2026: Sessão 3, simulação das segundas, correção da curva e Fases 1 e 2

- **Ferramenta:** Claude (chat com acesso aos dados e ao Mac).
- **O que pedi:** clonar o fork e conferir os dados com o download oficial do Kaggle (checksum); uma simulação das segundas (A/B do vendedor com e sem o Clima); produtividade por hora; adiantar as Fases 1 e 2 (dados e Clima) para eu revisar.
- **Onde a IA errou:**
  5. A curva da versão 1 só aprendia com deals fechados e dizia que deal velho era o melhor (76% aos 120 dias). A simulação mostrou o contrário: de 91 a 138 dias, só 21% ganharam e 69% nunca fecharam. Com essa curva, a lista perdia para o sorteio.
  6. A primeira conta do A/B somava o mesmo deal várias vezes. Na conta certa (cada deal uma vez), o ganho contra o feeling ficou em +5% e contra o maior valor em +52,5%.
- **O que decidi:** curva corrigida, que conta também os deals ainda abertos (tábua de sobrevivência, com a perda como risco concorrente); selo "esfriando" para deals de 91 a 138 dias, sem rótulo novo; `git add -f` nos commits, sem mexer no `.gitignore` do G4; Fases 1 e 2 sem commit até eu revisar; retirar do PRD o cenário de +$92 mil por mês (valia só entre deals que fecharam, não na segunda-feira do vendedor).
- **Achados:** na base, só deal aberto fica sem conta, então "sem conta" não pode virar sinal sem olhar o futuro; região e gerente passam no autoteste, mas não mudam a lista do vendedor (servem à visão do gerente).
- **Entregas:** Fases 1 e 2 com testes; PRD revisado (seções 5.2, 9 e 10).

## 02/10/2026 (noite): Sessão 4, Fase 3 e revisão independente no Claude Code

- **Ferramentas:** Claude (chat com acesso ao Mac) para construir; Claude Code local (Sonnet) para revisar e commitar.
- **O que pedi:** a Fase 3 (Score, rótulos de ação, frases e Raio X do Cliente) e uma revisão antes do commit.
- **Onde a IA errou:**
  7. Construiu a Fase 3 direto pela ponte com o Mac, sem perguntar se eu queria rodar no Claude Code, como estava no plano.
  8. O Raio X ignorava a data de referência: com uma data anterior, usaria vitórias e negociações do futuro. A revisão independente no Claude Code achou o erro; corrigido com 2 testes novos.
  9. O PRD dizia que o foco do vendedor mediano tinha 12 deals; o certo é 11.
- **O que decidi:** revisão independente antes de todo commit; a ficha da conta usa a mesma premissa do Clima (engage até a data de referência ou Prospecting); da Fase 4 em diante, desenvolvimento no Claude Code local.
- **Achado:** 6 de 27 vendedores não têm nenhum deal no foco (ex.: Darcel Schlecht, 194 abertos e nenhum para atacar).
- **Entregas:** commit `a5095e1` (`score: valor esperado, rótulos de ação e raio x`), 34 testes passando.

## 03/10/2026 (manhã e tarde): Sessão 5, teste de aceite e a virada para o vendedor

- **Ferramentas:** Claude Code local para a Fase 4 (app); Claude (chat) para revisar e decidir.
- **O que pedi:** o app da Fase 4 e, no meu teste de aceite, os ajustes.
- **O que o teste de aceite mostrou:** o app seguia o PRD ao pé da letra (6 abas, filtros de região e gerente) e era uma tela de gerente. Escrevi: "a tela que vejo é para um gerente e não para um vendedor (...) temos que trabalhar do vendedor para fora". O pedido da Head de RevOps era "uma ferramenta que o vendedor abra, veja o pipeline e saiba onde focar". Também vi "Atacar agora" em vermelho: vermelho manda o sinal de parar.
- **Onde a IA errou:**
  10. Ao explicar um deal, a IA usou um preço errado para o GTK 500 e um Score que ela mesma inventou, sem rodar os dados. Desconfiei da explicação e cobrei: "você alucinou e levou todo o projeto para outro lado". A IA conferiu os arquivos, admitiu a invenção e corrigiu. Regra nova a partir daí: nenhum número sem rodar o código.
- **O que decidi:** vendedor primeiro, gerente depois; o vendedor vê só os deals dele; verde e azul para as ações de foco, vermelho só para alerta; manter Streamlit (cabe no prazo e no "simples, mas precisa funcionar" do desafio); refazer a interface tela a tela.
- **Revisão de PMO na mesma tarde:** a IA listou o que travava a submissão (README vazio, process log só com a sessão 1, testes sem rodar no Mac, PR não aberto).

## 03/10/2026 (tarde): Sessão 6, novos sinais para o Clima e o fator carga

- **Ferramenta:** Claude (chat com acesso ao Mac).
- **O que pedi:** testar mais parâmetros no Clima (tempo aberto, faturamento, setor, histórico de compra, engajamento em redes sociais, localização, vendedor), sempre nos dados reais.
- **Onde a IA errou:**
  11. O primeiro script exploratório calculou os fatores sem separar treino e teste no tempo e deu um resultado bom demais. Ao rodar o autoteste do projeto (aprende antes de 01/07/2017, testa depois), vendedor, setor e conta caíram: no período de teste, o sinal se inverteu.
  12. Na implementação do fator carga, a IA sugeriu um modelo menor (Haiku) por ser "dev repetitivo", reescreveu o `clima.py` inteiro (o combinado era edição pontual), renomeou um campo e quebrou 1 teste sem rodar o pytest. Só apareceu na auditoria da sessão 7.
  13. O README escrito nessa sessão tinha números que o código do repositório não reproduz: "+$90k sobre o modelo só por idade" (era contra o feeling, e o fator carga nem entrava na simulação), "+15,7 pontos robustos em 3 janelas", uma estratégia "Maior Chance" que não existe e um teto de 95% que o código não aplica.
- **O que decidi:** engajamento em redes sociais não existe na base, então vira melhoria da v2, não dado inventado; testar mais 8 candidatos com o mesmo rigor, em testes feitos na conversa, sem script no repositório (produto, série, mês, dia da semana, faixa de preço e especialização do vendedor caíram; região passou, mas não muda a lista do vendedor; a carga passou); incluir a carga de pipeline do vendedor (quantos deals ele tinha abertos quando o deal começou), com o risco de causalidade reversa declarado como limitação.
- **Entregas:** `FATOR_CARGA` no `clima.py`. O prompt preparado para essa tarefa está em [`prompts/prompt-fator-carga.md`](prompts/prompt-fator-carga.md): pedia edição pontual, pytest e comparação na simulação, e a execução não cumpriu os três.

## 03/10 (noite) a 04/10/2026: Sessão 7, tela do vendedor e auditoria final

- **Ferramentas:** Claude no app desktop, com acesso ao Mac (Sonnet para o mockup e o app, Opus para a auditoria). Mockup clicável feito como artefato de design no próprio Claude.
- **O que pedi:** primeiro um mockup da tela do vendedor para ajustar antes de codar; depois o app de verdade; no fim, uma auditoria do repositório contra o guia de submissão.
- **Iterações do mockup:** duas telas (lista do vendedor e detalhe do lead, com as abas Raio X e Playbook). Meu retorno: "falta explicar por que o score do cliente e por que a probabilidade, para atender o requisito 'O vendedor (não-técnico) consegue usar e entender?'"; dicas para reverter os selos "esfriando" e "sem cadastro"; nomes de grupo que um leigo entenda; não pensar ainda na visão do gerente. O Playbook ficou genérico, por regra, e os dados comportamentais que a metodologia do Alfredo pede viraram sugestão para a v2.
- **Onde a IA errou:**
  14. Dois valores em dólar no mesmo texto viravam fórmula matemática no Streamlit (o `$...$`). A primeira checagem procurou só no `app.py` e não viu que a frase vem pronta do `score.py`. Achado na auditoria, lendo o `score.py`, corrigido no app (sem mexer no `score.py`) e conferido nos prints.
  15. A auditoria achou o que tinha passado nas sessões anteriores: `.claude/launch.json` commitado fora da pasta da submissão (o CONTRIBUTING rejeita esse PR); README fora do template e sem instruções de setup; o teste quebrado da sessão 6; um parâmetro do Streamlit marcado para sair na próxima versão; o subtítulo "boa chance de fechar" no grupo "Atacar agora", que também tem deals esfriando com 9% de chance; a dica de "esfriando" sumia quando o deal também estava sem cadastro; e "Atacar agora" ainda em vermelho, contra a decisão da sessão 5.
- **Como verifiquei:** rodei a simulação oficial (`python -m lead_scorer.validacao`) e refiz o teste do fator carga num script versionado (`solution/analises/fator_carga.py`). Resultado: a carga não muda a receita (-0,04%), sobe o acerto semanal de 48,2% para 49,3% e a nota de ordenação de 0,652 para 0,667; a diferença de taxa de ganho entre pouca e muita carga fica entre +6 e +9 pontos, não os +15,7 do autoteste da sessão 6 (que não ficou no repositório). Instalei tudo do zero numa máquina limpa (Streamlit 1.65): 34 testes passando. Os prints do README saíram do app rodando. Por fim, um revisor separado, que não viu o trabalho, clonou a branch, refez cada número do README a partir do código, repetiu os testes com Python 3.10 e as versões mínimas do `requirements.txt` e apontou ajustes de texto, já aplicados.
- **O que decidi:** visão do gerente fora desta entrega (o desafio pede a tela do vendedor); score preditivo com dados comportamentais fica para a v2; README reescrito no template, só com números reproduzíveis; manter o fator carga, documentado com o número certo; abrir o PR só depois da minha revisão.
- **Entregas:** tela do vendedor (`solution/app.py`), prints em `docs/screenshots/`, `solution/analises/fator_carga.py`, este log e o README.
