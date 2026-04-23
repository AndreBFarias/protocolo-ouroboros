# Sprint 86 — Ressalvas do caminho crítico IOTA + KAPPA (checklist humano)

**Status:** BACKLOG
**Prioridade:** P1 (pré-requisito para considerar IOTA/KAPPA 100% verdes)
**Dependências:** todas as Sprints 68b, 70–81
**Issue:** RESSALVA-IOTA-KAPPA-HUMANO
**Formato:** checklist sem código — cada item é uma ação que o André precisa executar pessoalmente

## Contexto

Durante a execução do caminho crítico IOTA + KAPPA (2026-04-22, 14 sprints),
Claude acumulou 20 ressalvas formais. Parte delas exige ação humana: instalar
dependências do sistema, validar visualmente o dashboard, aprovar decisões
arquiteturais, popular dados em volume real. Essas são consolidadas aqui.

A Sprint 87 (companheira) lista o débito que Claude pode resolver
autonomamente — estas duas sprints, juntas, fecham o ciclo IOTA/KAPPA.

## Como marcar progresso

Após executar cada item, substitua `[ ]` por `[x]` na frente da linha. Ao
marcar todos, a Sprint 86 está pronta para move para `concluidos/`.

## 1. Ambiente (bloqueia testes de grafo visual)

- [ ] **86.1 — Instalar libbz2-dev e recompilar Python via pyenv.** O Python 3.12.1 atual no `.venv` foi compilado sem `_bz2`, o que quebra `import networkx` (dependência transitiva de `pyvis`). Sem isso, a Sprint 78 (grafo Obsidian-like full-page) roda com placeholder `<p>pyvis não instalado</p>`. Passos:
  - Ubuntu/Debian: `sudo apt install libbz2-dev libffi-dev libssl-dev zlib1g-dev`
  - Arch/Manjaro: `sudo pacman -S bzip2`
  - macOS: `brew install bzip2 xz openssl@3`
  - Depois: `pyenv uninstall 3.12.1 && pyenv install 3.12.1 && rm -rf .venv && ./install.sh`
  - Validar: `.venv/bin/python -c "import pyvis; print(pyvis.__version__)"` deve imprimir versão
  - Rodar `.venv/bin/pytest tests/test_grafo_filtrado.py -v` e ver **16 passed / 0 skipped** (hoje: 11 passed / 5 skipped)

Isso deveria estar no install.sh automaticamente, pode fazer isso pra gente? Caso necessário use 10203040 na senha sudo.

- [ ] **86.2 — Confirmar que `~/Controle de Bordo/` está com backup antes de rodar sync rico em modo executar.** A Sprint 71 escreve em `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}`. O módulo respeita `sincronizado: true` + tag `#sincronizado-automaticamente` para não sobrescrever edição manual, mas se houver notas antigas em outros paths próximos (ex: um `Pessoal/Casal/Financeiro/` pré-existente), convém snapshotar antes.
  - Comando de backup: `cp -r "$HOME/Controle de Bordo" "$HOME/Controle de Bordo.backup-$(date +%Y%m%d)"`

## 2. Validação visual no dashboard (bloqueia aceitação UX)

Rode `./run.sh --dashboard`, faça login, e execute cada verificação:

- [ ] **86.3 — Sprint 76 (logo + fonte 13px + padding).** Abrir viewport 1600x1000. Conferir em 3 páginas (Visão Geral, Grafo + Obsidian, IRPF):
  - Logo `assets/icon.png` visível na sidebar, centralizado, acima do título "Protocolo Ouroboros"
  - Nenhum texto do corpo está abaixo de 13px (inspecionar via DevTools → Elements)
  - Nenhum parágrafo está colado na borda do retângulo principal (`.main .block-container` com padding >= 16px)
  - Capturar screenshot em `docs/mockups/sprint_76_DEPOIS_{pagina}.png` (opcional, para histórico)

- [ ] **86.4 — Sprint 77 (treemap + legendas + filtros avançados).**
  - Aba Categorias: treemap "Gastos por Categoria" com bordas escuras entre quadrados (não mais visual plano), fonte monospace, texto no centro
  - Nenhum texto do treemap cortado/quebrado (se aparecer `…`, reduzir min-size ou alargar janela)
  - Aba Extrato → expander "Filtros avançados": mudar Categoria para "Farmácia" e confirmar que contador "N transações encontradas" cai
  - Mudar filtro Classificação para "Obrigatório" e confirmar redução
  - Nenhum plot tem legenda sobrepondo título (qualquer página com plotly)

- [ ] **86.5 — Sprint 72 + 73 (filtro forma + drill-down).**
  - Sidebar: mudar "Forma de pagamento" para "Crédito" → KPIs (Receita/Despesa/Saldo) devem recalcular. Abas Extrato, Categorias, Visão Geral, Projeções, Contas, Análise devem refletir.
  - Aba Categorias: clicar em quadrado do treemap → URL deve virar `?tab=Extrato&categoria=X` e Extrato deve abrir filtrado
  - Extrato deve mostrar breadcrumb "categoria: X ×"; clicar no × remove o filtro

- [ ] **86.6 — Sprint 74 (modal de transação com preview).**
  - Aba Extrato → rolar até "Inspecionar transação" → escolher linha com categoria "Natação" ou similar → clicar "Ver detalhes"
  - Modal deve abrir com metrics (Data/Valor/Categoria/Banco) e seção "Estado" colorida
  - Se não houver comprovante vinculado: mensagem "Nenhum comprovante vinculado" e caption explicativa
  - (Quando Sprint 87 item 87.3 for concluída): modal mostrará o PDF embedado

- [ ] **86.7 — Sprint 78 (grafo Obsidian-like).** Pré-requisito: item 86.1 concluído.
  - Aba Grafo + Obsidian → expander "Grafo Full-Page" no topo
  - Slider "Limite de nós" = 500, toggle "Órfãos" = off, tipos default
  - Canvas ocupa pelo menos 70% da largura; painel lateral com filtros legenda visível
  - Tempo total de render < 3s (subjetivo; se demora > 5s, algo errado)
  - Clicar em nó fornecedor → URL muda para `?tab=Extrato&fornecedor=X` → aba Extrato abre filtrada

- [ ] **86.8 — Sprint 75 (completude).**
  - Aba Completude → heatmap mês × categoria visível
  - Alertas inteligentes aparecem quando há recorrência / zero-cobertura (hoje quase tudo é zero-cobertura, é o sinal esperado)
  - Botão "Exportar transações sem comprovante (CSV)" funciona → CSV com colunas `mes_ref`, `categoria`, `data`, `valor`, `local`, `banco_origem`, `identificador`

- [ ] **86.9 — Sprint 79 (aba Pagamentos).**
  - Aba Pagamentos → 3 sub-abas (Boletos / Pix / Crédito)
  - Boletos: metrics (Pagos/Pendentes/Atrasados) coerentes; se algum prazo for atrasado, deve aparecer
  - Alertas de vencimento aparecem para boletos pendentes nos próximos 3 dias
  - Pix: bar chart horizontal com top 20 beneficiários; total = soma visível
  - Crédito: line chart por banco (Nubank Cartão aparece? Santander Cartão?)

## 3. Decisões arquiteturais aguardando aprovação

- [ ] **86.10 — Sprint 80: trocar `./run.sh` sem args para invocar menu Python?** Hoje o `./run.sh` sem args abre o menu bash existente (rico, com processar_mes específico e backup). A Sprint 80 introduziu `./run.sh --menu` que abre o menu Python+rich. Decidir:
  - (a) Manter status quo: `./run.sh` bash continua default; `./run.sh --menu` explícito para Python
  - (b) Promover Python a default: editar `run.sh` para que `case "${1:-}"` trate sem-args como `--menu`
  - Decisão documentada em `docs/ROADMAP.md` ou em uma nota curta

- [ ] **86.11 — Sprint 70 (R70-1): como resolver pessoa=casal para boletos SESC?**
  - GTC-01 esperava `data/raw/andre/boletos/` mas o boleto foi para `data/raw/casal/boletos/` porque o `pessoa_detector` busca CPF no conteúdo do PDF, e boleto de SESC não carrega CPF do pagador. Opções:
  - (a) Heurística por nome de arquivo (`natacao_andre.pdf` → `andre`)
  - (b) Extrator de boleto que capture "Pagador: ANDRE..." quando existe
  - (c) Aceitar `casal/` como canônico para boletos compartilhados
  - Decisão afeta Sprint 87 item 87.4

## 4. Ingestão em volume real (pré-requisito para Sprint 75/78 terem dados)

- [ ] **86.12 — Rodar `./run.sh --inbox` com inbox populada.**
  - Pré-requisito: jogar arquivos reais em `~/Controle de Bordo/Inbox/` ou em `./inbox/` (raiz do projeto)
  - O adapter vai preservar originais em `data/raw/originais/` e mover para `data/raw/{pessoa}/{tipo}/`
  - Depois: rodar `.venv/bin/python scripts/reprocessar_documentos.py` para popular nodes de documento no grafo

- [ ] **86.13 — Rodar `./run.sh --tudo` para reprocessar o XLSX.**
  - Gera o XLSX final em `data/output/ouroboros_2026.xlsx` com todas as transações + tags IRPF + resumo mensal
  - Conferir que `make smoke` continua 8/8 OK após o reprocessamento

- [ ] **86.14 — Rodar `.venv/bin/python -m src.obsidian.sync_rico --executar` para sync rico bidirecional com o vault.**
  - Conferir que notas aparecem em `~/Controle de Bordo/Pessoal/Casal/Financeiro/Documentos/{YYYY-MM}/`
  - Abrir Obsidian e conferir que o grafo mostra as novas notas conectadas via wikilinks

## 5. Documentação

- [ ] **86.15 — Atualizar `CLAUDE.md` com novas contagens.**
  - Pós-reprocessamento, executar `.venv/bin/python -m src.graph.queries` e copiar contagens de nodes/edges/IRPF tags para a seção de cabeçalho do `CLAUDE.md`
  - Atualizar contagem de testes (hoje baseline é 1046 passed / 15 skipped; se item 86.1 rodou, vira 1051 / 10)

- [ ] **86.16 — Criar anúncio informal da conclusão do caminho crítico.**
  - Para histórico pessoal / postfacing com Vitória. Não precisa ser longo — só deixar registrado que "Fases IOTA e KAPPA completas em 2026-04-22".

---

## Critério de aceitação da Sprint 86

A sprint é considerada CONCLUÍDA quando pelo menos:

- Items **86.1** (ambiente), **86.12**, **86.13**, **86.14** (ingestão em volume) estão marcados
- Pelo menos 5 dos items de validação visual (86.3 – 86.9) estão marcados
- Items **86.10** e **86.11** (decisões arquiteturais) têm resposta registrada

Os items restantes podem virar achados colaterais para sprints futuras — não bloqueiam o fechamento da 86 porque são polish de segunda ordem.

---

*"Algumas coisas só se resolvem com olho humano e dedo humano." — princípio que honra a sessão de 2026-04-22*
