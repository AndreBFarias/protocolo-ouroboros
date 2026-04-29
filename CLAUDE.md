# CLAUDE.md — Protocolo Ouroboros

> **Constituição técnica.** Regras invioláveis, invariantes, workflow.
> Para estado atual (testes, sprints abertas, métricas), ver `contexto/ESTADO_ATUAL.md`.
> Para histórico de sessões, ver `docs/HISTORICO_SESSOES.md`.
> Para visão humana e contexto, ver `contexto/POR_QUE.md`.

---

## Missão

Pipeline ETL financeiro pessoal para o casal André e Vitória, evoluindo para central de vida adulta (saúde, identidade, acadêmico, profissional). Centraliza dados de múltiplas fontes (bancos, NFs, holerites, documentos pessoais) em XLSX consolidado + dashboard Streamlit + grafo SQLite + integração Obsidian + bridge para companion mobile.

**Princípio:** a IA toma decisões técnicas. Ao receber arquivos novos, ela lê, classifica, extrai, deduplica, vincula e apresenta. Sem perguntas desnecessárias.

---

## Regras invioláveis

1. **Acentuação PT-BR correta** em código, commits, docs, comentários, variáveis em português. Nunca "funcao", "validacao". Sempre "função", "validação".
2. **Zero emojis** em código, commits, docs e respostas.
3. **Zero menções a IA** em commits e código (Claude, GPT, Anthropic). Hook bloqueia.
4. **Local First** — tudo offline. APIs externas são opcionais.
5. **Nunca `print()`** em produção. Logging via `rich` + `logging` com rotação.
6. **Nunca inventar dados.** Se não reconhecer, log warning + pular.
7. **Nunca remover código funcional** sem autorização explícita.
8. **`data/` inteiro no .gitignore** — dados financeiros nunca no repo.
9. **Paths relativos via `Path`** — nunca hardcoded absolutos.
10. **Citação de filósofo** como comentário final de todo arquivo `.py` novo.

---

## Armadilhas críticas

Aprendizados que precisam ser respeitados em qualquer mudança. Detalhes em `docs/ARMADILHAS.md`.

| # | Armadilha | Solução |
|---|-----------|---------|
| 1 | C6 XLS encriptado | `msoffcrypto-tool` decripta antes do `xlrd` |
| 2 | Itaú PDF protegido | Senha via `mappings/senhas.yaml` + `pdfplumber`. Nunca `PyPDF2` |
| 3 | Nubank tem 2 formatos CSV incompatíveis | Cartão: `date,title,amount`. CC: `Data,Valor,Identificador,Descrição` |
| 4 | Ki-Sabor mesmo local 2 categorias | Valor ≥ R$ 800 = Aluguel. < R$ 800 = Padaria |
| 5 | Categorizer com `return` em vez de `break` | `break` para que classificação N/A sempre execute |
| 6 | Histórico XLSX antigo com classificações corrompidas | "Obrigatórios" (com s), "Rou" (truncado) — normalizar |
| 7 | Prazos no XLSX antigo: índices errados | 2/3 no histórico, não 0/1 |
| 8 | Git push requer SSH alias | `git@github.com-personal:AndreBFarias/protocolo-ouroboros.git` |
| 9 | Pre-commit `core.hooksPath` global | Usar script local `scripts/pre-commit-check.sh` |
| 10 | Tesseract OCR para energia | Valores R$ 100% precisos. Consumo kWh 67% (layout do app confunde) |
| 11 | Streamlit tabs trocam visualmente | Requer JavaScript (`document.querySelectorAll('[role="tab"]')[N].click()`) |
| 12 | Santander "Black Way" | Cartão Elite Visa, final 7342 |
| 13 | Nubank CC tem duplicatas "(1)" "(2)" | Deduplicação por UUID é essencial |
| 14 | `msoffcrypto-tool` é dependência crítica | Sem ela, C6 XLS não abre |

---

## Identificação de arquivos

A IA deve ler o **conteúdo** (não confiar no nome) para detectar:

| Pista no conteúdo | Banco/Fonte |
|-------------------|-------------|
| "ITAÚ UNIBANCO", "itau.com.br", agência 6450 | Itaú — extrato CC |
| "SANTANDER", "4220 XXXX XXXX 7342" | Santander — fatura cartão |
| "NU PAGAMENTOS", "NUBANK", "Nu Financeira" | Nubank |
| "BCO C6 S.A.", "31.872.495" | C6 Bank |
| CSV: `date,title,amount` | Nubank cartão |
| CSV: `Data,Valor,Identificador,Descrição` | Nubank CC |
| "Neoenergia", "CEB", "Kwh" | Conta de energia (OCR) |
| "CAESB", "Saneamento" | Conta de água |
| Holerite com "G4F SOLUCOES CORPORATIVAS" | G4F (André) |
| Holerite com layout Infobase | Infobase (André) |
| DAS PARCSN com CNPJ 00.394.460/0001-41 | Receita Federal |

---

## Schema do XLSX (8 abas)

### `extrato` (tabela principal)

| Coluna | Tipo | Obrigatório |
|--------|------|-------------|
| data | date | sim |
| valor | float | sim |
| forma_pagamento | str (Pix/Débito/Crédito/Boleto/Transferência) | sim |
| local | str | sim |
| quem | str (André/Vitória/Casal) | sim |
| categoria | str | sim |
| classificacao | str (Obrigatório/Questionável/Supérfluo/N/A) | sim |
| banco_origem | str | sim |
| tipo | str (Despesa/Receita/Transferência Interna/Imposto) | sim |
| mes_ref | str (YYYY-MM) | sim |
| tag_irpf | str ou null | não |
| obs | str | não |

### `renda`

Fonte primária: extrator de contracheque PDF (`src/extractors/contracheque_pdf.py`). Suporta G4F e Infobase. Folha mensal, 13º adiantamento e 13º integral são entradas distintas via campo `fonte`. Para meses sem holerite, recai para receitas inferidas do extrato bancário (INSS/IRRF/VR-VA ficam vazios).

### `dividas_ativas`, `inventario`, `prazos` (snapshots históricos 2022-2023)

**AVISO**: dados importados do `controle_antigo.xlsx`, **nunca atualizados automaticamente**. Aba do XLSX tem cabeçalho `[Snapshot histórico 2023 — dados não atualizados]` na **linha 1**; colunas começam na **linha 2**. Dashboard lê direto da linha 2 (Sprint 64 reabilita aviso na UI). Reabilitação depende de automação bancária (Sprint 24).

| Aba | Linhas | Conteúdo |
|---|---|---|
| `dividas_ativas` | 26 | mes_ref, custo, valor, status, vencimento, quem, recorrente, obs |
| `inventario` | 18 bens | bem, valor_aquisicao, vida_util_anos, depreciacao_anual, perda_mensal |
| `prazos` | 6 prazos | conta, dia_vencimento, banco_pagamento, auto_debito (leitura frágil — índices 2/3, não 0/1) |

### `resumo_mensal` (gerada automaticamente)

Colunas: mes_ref, receita_total, despesa_total, saldo, top_categoria, top_gasto, total_obrigatorio, total_superfluo, total_questionavel.

### `irpf`

CNPJ/CPF extraídos contextualmente pelo tagger (`src/transform/irpf_tagger.py`) a partir do campo `_descricao_original` das transações.

| Coluna | Tipo | Preenchido? |
|--------|------|-------------|
| ano | int | sim |
| tipo | str | sim (5 categorias: pagador, fonte_renda, despesa_dedutivel, deducao_legal, imposto_pago) |
| fonte | str | sim |
| cnpj_cpf | str | sim quando descrição bruta contém CNPJ/CPF (~75/164 = 44%) |
| valor | float | sim |
| mes | str | sim |

### `analise`

Aba viva desde Sprint 53. Visualizações ricas na página "Análise" do dashboard: Sankey de fluxo de categorias, heatmap mensal, bar charts de top fornecedores, cobertura de itens. Resumo narrativo textual permanece pendente (Sprint 33, ZETA).

---

## Categorização

Regras em `mappings/categorias.yaml`. Overrides manuais em `mappings/overrides.yaml`. Tags IRPF em `src/transform/irpf_tagger.py`.

**Ordem de prioridade:** overrides > regras regex > fallback (`Outros` + `Questionável`).

**Classificações válidas:** `Obrigatório`, `Questionável`, `Supérfluo`, `N/A` (transferências internas e receitas).

**Regra de ouro:** se não reconhecer, marca como `Outros` + `Questionável`. Nunca inventar.

---

## Deduplicação

3 níveis implementados:
1. **UUID** — Nubank CC tem identificador único.
2. **Hash** — `hash(data + local + valor)` para cruzar fontes diferentes.
3. **Pares de transferência** — Saída Itaú = entrada Nubank → marca como `Transferência Interna`.

Transferências entre contas próprias **não são gastos**.

---

## Detecção de pessoa

- Bancos do André (Itaú, Santander, C6, Nubank cartão) → `André`
- Bancos da Vitória (Nubank PF 97737068-1, PJ 96470242-3) → `Vitória`
- Indeterminado → `Casal`
- PIX para Vitória → `Transferência Interna`, não gasto

Identificadores específicos em `mappings/pessoas.yaml` (gitignored, PII).

---

## Senhas

PDFs bancários protegidos. Senhas em `mappings/senhas.yaml` (gitignored). Se ausente, perguntar ao usuário.

---

## Workflow obrigatório — Protocolo de validação tripla

Toda sprint passa por **3 fases de validação** explícitas. O Claude valida antes (não chuta), durante (não atropela), e depois (não declara concluído sem prova). Saltar qualquer fase = sprint REPROVADA.

### Fase ANTES (validação preventiva — antes de qualquer linha de código)

1. **Ler contexto canônico em ordem**: `contexto/POR_QUE.md` → `contexto/ESTADO_ATUAL.md` → `contexto/COMO_AGIR.md` → `CLAUDE.md` → spec da sprint.
2. **Ler ADRs referenciados** na spec (se houver).
3. **Ler `docs/ARMADILHAS.md`** quando o tema toca extrator, dedup, encoding.
4. **Validar a hipótese da spec com `grep` antes de codar.** A hipótese **não é dogma** — se grep contraria a spec, escrever achado-bloqueio e consultar o supervisor antes de prosseguir. (Padrão canônico VALIDATOR_BRIEF rodapé `(k)`.)
5. **Rodar `make lint` + `make smoke` + `pytest`** para confirmar estado verde **antes** de mexer. Vermelho herdado é dívida que precisa ser endereçada antes (não depois).
6. **Capturar baseline**: `pytest --collect-only -q | tail -1` registra contagem para comparar no final.

### Fase DURANTE (validação contínua — enquanto codifica)

1. **Edit incremental, não rewrite.** Preserve histórico — nunca apague código funcional sem autorização explícita.
2. **Testar incrementalmente** após cada mudança não-trivial: `pytest tests/test_<area>.py`.
3. **Lint inline**: rodar `ruff check <arquivo>` antes de salvar arquivo grande.
4. **Acentuação em todo código novo** — PT-BR ortograficamente correto.
5. **Validar invariantes do domínio** quando relevante: 8 abas do XLSX intactas, schema do grafo (`node`/`edge`) preservado, contratos do smoke aritmético (10/10) em qualquer momento.
6. **Achado colateral durante a execução**: NUNCA corrigir dentro da sprint atual (escopo creep) e NUNCA deixar `# TODO`. Criar **sprint-filha formal** em `docs/sprints/backlog/` ou Edit-pronto na hora.
7. **Trabalhar em worktree** quando a sprint for substantiva: `cd "$WORKTREE_PATH" && ...` + `git rev-parse --show-toplevel` antes de cada commit. (Padrão canônico VALIDATOR_BRIEF rodapé `(j)`.)

### Fase DEPOIS (validação de fechamento — gate anti-migué de 9 checks)

Sprint só vira **CONCLUÍDA** quando todos passam:

1. **Hipótese declarada validada com grep** antes de codar (Fase ANTES item 4).
2. **Proof-of-work runtime real** capturado em log: `python -m <módulo>` ou `./run.sh --<flag>` mostra o efeito esperado em dados reais.
3. **Quando aplicável: gate 4-way ≥3 amostras** (`make conformance-<tipo>`) verde — bloqueante para extratores novos a partir do plan pure-swinging-mitten.
4. **`make lint` exit 0**.
5. **`make smoke` 10/10 contratos**.
6. **`pytest tests/ -q` baseline mantida ou crescida**. Comparar com baseline da Fase ANTES.
7. **Achados colaterais viraram sprint-ID OU Edit-pronto**. Zero "TODO depois", zero issue informal.
8. **Validador (humano OU subagent) APROVOU**. Auto-aprovação proíbida.
9. **Spec movida** de `docs/sprints/backlog/` para `docs/sprints/concluidos/` com frontmatter `concluida_em: YYYY-MM-DD` e link para o commit.

### Resumo do protocolo

```
ANTES   ─→ ler/validar/medir baseline (não chutar)
DURANTE ─→ edit incremental + testes contínuos + zero TODO solto
DEPOIS  ─→ 9 checks anti-migué OU sprint REPROVADA
```

**Atalho `make anti-migue`** (Sprint MAKE-AM-01): roda `lint`, `smoke`, `test` e valida frontmatter `concluida_em` em todas as specs concluídas em sequência. Use como entry point único do gate antes de mover qualquer spec para `concluidos/`. O target `make conformance-<tipo>` será habilitado quando ANTI-MIGUE-01 implementar o gate 4-way.

### Padrão canônico de commit

- PT-BR imperativa, formato `tipo: descrição` (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`).
- Máximo 70 caracteres na primeira linha.
- Corpo opcional com **WHY**, não WHAT.
- **Nunca** mencionar Claude, GPT, Anthropic, IA. Hook commit-msg bloqueia.
- Escolher mensagem que descreva o que mudou e por quê — diff conta o quê.

---

## Convenções

- PT-BR em tudo (código, comentários, outputs).
- Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`. PT-BR imperativa.
- Datas ISO 8601 (YYYY-MM-DD).
- Valores float com 2 casas decimais.
- Limite de 800 linhas por arquivo (exceto config e testes).
- Sem `# TODO` ou `# FIXME` inline (criar issue ou sprint-filha formal).
- Sem nomes pessoais em docstrings ou commits.
- PII (CPF/CNPJ pessoal) nunca em log INFO. Mascarar como `XXX.XXX.XXX-XX`.

---

## ADRs ativos

Princípios que regem qualquer decisão estrutural. Leitura obrigatória antes de mudança arquitetural.

- **ADR-07** — Local First.
- **ADR-08** — Supervisor-Aprovador LLM (Claude propõe, humano aprova).
- **ADR-09** — Autossuficiência Progressiva (LLM é provisório; métrica = % determinístico).
- **ADR-10** — Resiliência a Dados Incompletos.
- **ADR-11** — Classificação em Camadas (overrides > regex > LLM > fallback).
- **ADR-12** — Cruzamentos via Grafo de Conhecimento.
- **ADR-13** — Supervisor artesanal via Claude Code (sessão interativa, sem API programática).
- **ADR-14** — Grafo SQLite extensível.
- **ADR-15** — Intake universal multiformato.
- **ADR-18** — Integração com sistema vivo (Controle de Bordo).
- **ADR-19** — Dashboard interativo com drill-down.
- **ADR-20** — Tracking documental completo.
- **ADR-21** — Fusão Ouroboros + Controle de Bordo (visão OMEGA).
- **ADR-22** — Navegação por clusters.

---

## Cobertura conhecida vs gaps

Snapshot da auditoria honesta 2026-04-29 (detalhe completo em `~/.claude/plans/pure-swinging-mitten.md`).

**Funciona hoje:**
- Pipeline ETL maduro (22 extratores, 6.094 transações, smoke 10/10).
- Categorização 100% (regex YAML + overrides).
- Linking transação ↔ documento parcial (~50% docs vinculados desde Sprint 95).
- Dashboard 13 abas em 5 clusters; Revisor 4-way (ETL × Opus × Grafo × Humano).
- Vault Obsidian sync via `sync_rico` em `~/Controle de Bordo/Pessoal/Casal/Financeiro/`.
- Reserva de emergência: 100% atingida.

**Gaps P0 ainda abertos** (bloqueiam "central de vida adulta de verdade"):
- ADR-08 (Supervisor LLM): 0% implementado — Onda 2 do plan.
- 8 documentos cotidianos sem regra YAML (Amazon, PIX foto, exame médico, RG/CNH, diploma, etc.) — Onda 3.
- Multi-foto do mesmo doc causa duplicação garantida — DOC-13.
- DANFE retorna `[]` sem validar ingestão — DOC-16.
- Mobile bridge não-auditado (Mob-Ouroboros companion) — Onda 5.
- Vault Obsidian sem monitor de dessincronia — MON-01.

**Gaps P1**: 13 itens (acessibilidade WCAG, OCR energia frágil, holerites fora G4F+Infobase, integrações Calendar/Email/Assinaturas inexistentes, ADRs adjacentes não-implementadas).

---

## Estrutura do projeto

```
protocolo-ouroboros/
├── CLAUDE.md                     # Constituição técnica (este arquivo)
├── contexto/                     # POR_QUE, ESTADO_ATUAL, COMO_AGIR, PROMPT_NOVA_SESSAO
├── pyproject.toml                # Dependências
├── Makefile                      # 13 targets
├── install.sh                    # Setup completo
├── run.sh                        # Entrypoint (--mes, --tudo, --inbox, --dashboard, --sync, --full-cycle, --reextrair-tudo)
│
├── data/                         # TUDO no .gitignore
│   ├── raw/{pessoa}/{banco}/     # Brutos por pessoa e banco
│   ├── processed/                # CSVs intermediários
│   ├── output/                   # XLSX final + relatórios + grafo.sqlite
│   └── historico/                # XLSX antigo importado
│
├── src/
│   ├── pipeline.py               # Orquestrador
│   ├── inbox_processor.py        # Detecta, renomeia, move
│   ├── intake/                   # Classifier, registry, dedup, anti-órfão
│   ├── extractors/               # 22 extratores (9 bancários + 13 documentais)
│   ├── transform/                # Categorizer, normalizer, deduplicator, irpf_tagger
│   ├── load/                     # xlsx_writer, relatório
│   ├── integrations/             # Belvo, Gmail, Controle de Bordo
│   ├── projections/              # Cenários financeiros
│   ├── dashboard/                # Streamlit (5 clusters, 13 abas)
│   ├── obsidian/                 # Sync com vault Obsidian
│   ├── graph/                    # Grafo SQLite + linking + ingestor_documento
│   └── utils/                    # logger, pdf_reader, file_detector, validator, parse_br
│
├── mappings/                     # Configurações declarativas
│   ├── categorias.yaml
│   ├── overrides.yaml
│   ├── tipos_documento.yaml
│   ├── inbox_routing.yaml
│   ├── pessoas.yaml              # PII, gitignored
│   └── senhas.yaml               # gitignored
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ARMADILHAS.md
│   ├── HISTORICO_SESSOES.md      # Diário cronológico
│   ├── adr/                      # 14 ADRs ativos
│   ├── sprints/                  # backlog, concluidos, arquivadas
│   └── extractors/               # Auto-doc por formato
│
├── scripts/
│   ├── smoke_aritmetico.py       # 8 contratos globais
│   └── pre-commit-check.sh
│
└── tests/                        # 2.018 passed (baseline 2026-04-29)
```

---

## Referências rápidas

| Recurso | Caminho |
|---------|---------|
| Categorização | `mappings/categorias.yaml` |
| Overrides manuais | `mappings/overrides.yaml` |
| Senhas PDFs | `mappings/senhas.yaml` (gitignored) |
| Validador | `python -m src.utils.validator` |
| Pipeline completo | `make process` ou `./run.sh --tudo` |
| Pipeline inbox+tudo | `./run.sh --full-cycle` |
| Reextrair com confirmação | `./run.sh --reextrair-tudo` |
| Dashboard | `make dashboard` |
| Sync Obsidian | `./run.sh --sync` |
| Lint | `make lint` |
| Smoke aritmético | `make smoke` |
| Sprints (backlog/concluidos/arquivadas) | `docs/sprints/` |
| Índice mestre de sprints + relacionamento antigas vs plan | `docs/SPRINTS_INDEX.md` |
| Plan ativo (auditoria + 6 ondas) | `~/.claude/plans/pure-swinging-mitten.md` |
| Blueprint da central de vida adulta (DESIGN-01) | `docs/BLUEPRINT_VIDA_ADULTA.md` |
| ADRs | `docs/adr/ADR-NN-*.md` |
| Estado atual | `contexto/ESTADO_ATUAL.md` |
| Histórico de sessões | `docs/HISTORICO_SESSOES.md` |
| Padrões canônicos do validador | `VALIDATOR_BRIEF.md` |

---

*"O dinheiro é um bom servo, mas um mau mestre." — Francis Bacon*
