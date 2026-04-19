# CLAUDE.md -- Protocolo Ouroboros

```
VERSÃO: 4.0 | STATUS: PRODUÇÃO (catalogador universal em construção) | LANG: PT-BR
TRANSAÇÕES: 6.136 | MESES: 82 (out/2019 a mar/2026) | BANCOS: 6 | EXTRATORES: 9
SPRINTS: 51 (20 concluídas, 0 produção, 18 backlog, 13 arquivadas)
CATEGORIZAÇÃO: 100% | IRPF TAGS: 167 (75 com CNPJ) | HOLERITES: 24 (G4F + Infobase)
TESTES: 44 unitários (transform/ 82% média, extractors/contracheque_pdf 59%)
ROTA: Catalogador universal artesanal via Claude Code Opus (ver docs/ROADMAP.md fases ALFA→ZETA)
SUPERVISOR: Claude Code (sessão interativa) -- nenhuma API programática (ADR-13)
INTEGRAÇÕES: OFX (pronto), Belvo (em teste), Gmail (setup pendente), MeuPluggy (disponível)
ROTA ATUAL: Plano 30/60/90 dias -- base honesta + supervisor IA + cérebro MVP
```

---

## Missão

Pipeline ETL financeiro pessoal para o casal André e Vitória. Centraliza dados bancários de múltiplas fontes em XLSX consolidado + dashboard Streamlit + relatórios mensais + integração Obsidian.

**Princípio:** a IA toma TODAS as decisões técnicas. Ao receber arquivos novos, ela lê, extrai, categoriza, deduplica e gera saída. Sem perguntas desnecessárias.

---

## Regras Invioláveis

1. **Acentuação correta** em TUDO: código, commits, docs, comentários, variáveis em português. Nunca "funcao", "validacao", "descricao" -- o correto é "função", "validação", "descrição". Sem exceção.
2. **Zero emojis** em código, commits, docs e respostas.
3. **Zero menções a IA** em commits e código (nomes como Claude, GPT, Anthropic). Commits limpos e anônimos.
4. **Local First** -- tudo funciona offline. APIs externas são opcionais.
5. **Nunca `print()`** em produção. Logging via `rich` + `logging` com rotação (5MB, 3 backups).
6. **Nunca inventar dados.** Se não reconhecer um arquivo, loga warning e pula.
7. **Nunca remover código funcional** sem autorização explícita.
8. **`data/` inteiro no .gitignore** -- dados financeiros nunca no repositório.
9. **Paths relativos via `Path`** -- nunca hardcoded absolutos.
10. **Citação de filósofo** como comentário final de todo arquivo .py.

---

## Armadilhas Críticas

Aprendizados das Sprints 1-4 que PRECISAM ser respeitados:

| # | Armadilha | Solução |
|---|-----------|---------|
| 1 | C6 XLS encriptado -- xlrd sozinho falha | Usar `msoffcrypto-tool` para decriptar ANTES, depois `xlrd` |
| 2 | Itaú PDF protegido | Senha via `senhas.yaml` + pdfplumber. Nunca PyPDF2 |
| 3 | Nubank tem 2 formatos CSV incompatíveis | Cartão: `date,title,amount`. CC: `Data,Valor,Identificador,Descrição` |
| 4 | Ki-Sabor: mesmo local, 2 categorias | Valor >= R$ 800 = Aluguel. Valor < R$ 800 = Padaria. Regra de valor |
| 5 | Categorizer: `return` após match impede fallback | Trocado por `break` para que classificação N/A sempre execute |
| 6 | Histórico: classificações corrompidas | "Obrigatórios" (com s), "Rou" (truncado) -- normalizar no pipeline |
| 7 | Prazos no XLSX antigo: colunas erradas | Índices 2/3 no histórico, não 0/1. Verificar ambos |
| 8 | Git push requer SSH alias | `git@github.com-personal:[REDACTED]/Financas.git` |
| 9 | Pre-commit: `core.hooksPath` global | Usar script local `scripts/pre-commit-check.sh`, não `pre-commit install` |
| 10 | Tesseract OCR para energia | Valores R$ = 100% precisos. Consumo kWh = 67% (layout do app confunde) |
| 11 | Streamlit tabs: troca visual | Requer JavaScript (`document.querySelectorAll('[role="tab"]')[N].click()`) |
| 12 | Santander "Black Way" | É o cartão Elite Visa, final 7342 |
| 13 | Nubank CC tem duplicatas "(1)" "(2)" | Deduplicação por UUID é essencial |
| 14 | `msoffcrypto-tool` é dependência crítica | Não é óbvio -- sem ela, C6 XLS não abre |

---

## Identificação de Arquivos

A IA deve ler o CONTEÚDO (não confiar no nome) para detectar:

| Pista no conteúdo | Banco/Fonte |
|-------------------|-------------|
| "ITAÚ UNIBANCO", "itau.com.br", agência 6450 | Itaú -- extrato CC |
| "SANTANDER", "4220 XXXX XXXX 7342" | Santander -- fatura cartão |
| "NU PAGAMENTOS", "NUBANK", "Nu Financeira" | Nubank |
| "BCO C6 S.A.", "31.872.495" | C6 Bank |
| CSV: `date,title,amount` | Nubank cartão (André ou Vitória PJ) |
| CSV: `Data,Valor,Identificador,Descrição` | Nubank CC (Vitória PF/PJ) |
| "Neoenergia", "CEB", "Kwh" | Conta de energia (OCR) |
| "CAESB", "Saneamento" | Conta de água |

---

## Schema do XLSX (8 abas)

### extrato (tabela principal)

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

### renda

Fonte primária: extrator de contracheque PDF (`src/extractors/contracheque_pdf.py`), que suporta G4F (PDF nativo) e Infobase (PDF nativo ou escaneado, com fallback OCR via tesseract). Folha mensal, 13º adiantamento e 13º integral são entradas distintas identificadas pelo campo `fonte`. Para meses sem holerite, o pipeline recai para receitas inferidas do extrato bancário (INSS/IRRF/VR-VA ficam vazios nesse caso).

| Coluna | Tipo | Preenchido? |
|--------|------|-------------|
| mes_ref | str (YYYY-MM) | sim |
| fonte | str | sim (G4F, Infobase, G4F - 13º Adiantamento, etc.) |
| bruto | float | sim (valor total dos vencimentos do contracheque) |
| inss | float | sim quando holerite disponível; vazio quando fallback para extrato bancário |
| irrf | float | idem |
| vr_va | float | idem (G4F tem Vale Alimentação; Infobase, não) |
| liquido | float | sim (valor líquido a receber do holerite) |
| banco | str | vazio para holerites; preenchido só para fallback de extrato |

### dividas_ativas

**AVISO:** Dados importados do controle_antigo.xlsx (2022-2023), nunca atualizados. As dívidas reais atuais (Nubank PF/PJ) não estão refletidas. 26 linhas estáticas. Aba no XLSX tem cabeçalho "[Snapshot histórico 2023 -- dados não são atualizados automaticamente]" na linha 1; colunas começam na linha 2.

| Coluna | Tipo |
|--------|------|
| mes_ref | str |
| custo | str |
| valor | float |
| status | str (Pago/Não Pago/Parcial) |
| vencimento | int |
| quem | str |
| recorrente | bool |
| obs | str |

### inventario

**AVISO:** 18 bens importados do histórico, sem mecanismo de atualização. Snapshot congelado. Cabeçalho de aviso na linha 1 do XLSX; colunas começam na linha 2.

| Coluna | Tipo |
|--------|------|
| bem | str |
| valor_aquisicao | float |
| vida_util_anos | int |
| depreciacao_anual | float |
| perda_mensal | float |

### prazos

**AVISO:** 6 prazos importados do histórico. Leitura frágil (depende de índices de coluna). Cabeçalho de aviso na linha 1 do XLSX; colunas começam na linha 2.

| Coluna | Tipo |
|--------|------|
| conta | str |
| dia_vencimento | int |
| banco_pagamento | str |
| auto_debito | bool |

### resumo_mensal (gerada automaticamente)

| Coluna | Tipo |
|--------|------|
| mes_ref | str |
| receita_total | float |
| despesa_total | float |
| saldo | float |
| top_categoria | str |
| top_gasto | str |
| total_obrigatorio | float |
| total_superfluo | float |
| total_questionavel | float |

### irpf

CNPJ/CPF extraídos contextualmente pelo tagger (`src/transform/irpf_tagger.py:_extrair_cnpj_cpf`) a partir do campo `_descricao_original` das transações. Em execução atual, 75 de 167 registros IRPF têm CNPJ/CPF preenchido (44%). Os que faltam são casos onde a descrição original não carrega os dígitos.

| Coluna | Tipo | Preenchido? |
|--------|------|-------------|
| ano | int | sim |
| tipo | str | sim |
| fonte | str | sim |
| cnpj_cpf | str | sim quando a descrição bruta contém CNPJ/CPF |
| valor | float | sim |
| mes | str | sim |

### análise

**AVISO:** Marcada como DEPRECATED no XLSX (linha 1 da aba). Produz apenas totais e contagens ("Total de X transações, top 10 categorias, balanço por pessoa"). Análise interpretativa real depende do resumo narrativo diagnóstico (Sprint 33, não implementada).

---

## Categorização

Regras em `mappings/categorias.yaml` (111 regras). Overrides manuais em `mappings/overrides.yaml` (prioridade sobre regex). Tags IRPF em `src/transform/irpf_tagger.py` (21 regras, 5 tipos).

**Ordem de prioridade:**
1. Overrides manuais (overrides.yaml)
2. Regras regex (categorias.yaml)
3. Fallback: `Outros` + `Questionável`

**Classificações válidas:** `Obrigatório`, `Questionável`, `Supérfluo`, `N/A`
- N/A: transferências internas e receitas (não são despesas classificáveis)
- Imposto: sempre `Obrigatório`

**Regra de ouro:** se não reconhecer, marca como `Outros` + `Questionável`. Nunca inventar categoria.

---

## Deduplicação

3 níveis implementados:
1. **UUID** -- Nubank CC tem identificador único. Elimina CSVs duplicados "(1)", "(2)"
2. **Hash** -- `hash(data + local + valor)` para cruzar fontes diferentes. Marca mas não remove
3. **Pares de transferência** -- Saída Itaú = entrada Nubank. Marca como `Transferência Interna`

Transferências entre contas próprias NÃO são gastos.

---

## Detecção de Pessoa

- Bancos do André (Itaú, Santander, C6, Nubank cartão) -> `André`
- Bancos da Vitória (Nubank PF 97737068-1, PJ 96470242-3) -> `Vitória`
- Indeterminado -> `Casal`
- PIX para Vitória = `Transferência Interna`, não gasto

---

## Senhas

PDFs bancários protegidos. Senhas carregadas de `mappings/senhas.yaml` (não rastreado pelo git).
Se o arquivo não existir, perguntar ao usuário.

---

## Workflow Obrigatório

### Antes de implementar
1. Ler `CLAUDE.md` e `GSD.md`
2. Ler a sprint atual em `docs/sprints/`
3. Ler `docs/ARMADILHAS.md`
4. `make lint` para verificar estado atual

### Ao implementar
1. Manter compatibilidade com pipeline existente
2. Testar incrementalmente (`make process` após cada mudança)
3. Verificar acentuação em todo código novo
4. Nunca quebrar as 8 abas do XLSX

### Antes de concluir
1. `make lint` (ruff check + format)
2. `make process` (pipeline completo)
3. `python -m src.utils.validator` (6 checagens de integridade)
4. Verificar dashboard se houver mudanças visuais
5. Commit com mensagem PT-BR no formato `tipo: descrição imperativa`

---

## Convenções

- PT-BR em tudo (código, comentários, outputs)
- Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Datas ISO 8601 (YYYY-MM-DD)
- Valores float com 2 casas decimais
- Limite de 800 linhas por arquivo (exceto config e testes)
- Sem `# TODO` ou `# FIXME` inline (criar issue no GitHub)
- Sem nomes pessoais em docstrings

---

## Estrutura do Projeto

```
protocolo-ouroboros/
├── CLAUDE.md                     # Este arquivo
├── GSD.md                        # Onboarding rápido para qualquer IA
├── README.md                     # Documentação pública
├── pyproject.toml                # Dependências Python
├── Makefile                      # 13 targets (help, install, process, dashboard...)
├── install.sh                    # Setup completo (venv + deps + tesseract)
├── run.sh                        # Entrypoint CLI (--mes, --tudo, --inbox, --dashboard, --sync)
├── .env                          # Senhas e paths (no .gitignore)
│
├── data/                         # TUDO no .gitignore
│   ├── raw/{pessoa}/{banco}/     # Arquivos brutos por pessoa e banco
│   ├── processed/                # CSVs intermediários
│   ├── output/                   # XLSX final + relatórios MD
│   └── historico/                # XLSX antigo importado
│
├── src/
│   ├── pipeline.py               # Orquestrador (11 passos, 8 extratores)
│   ├── inbox_processor.py        # Detecta, renomeia, move arquivos (.csv, .xlsx, .xls, .pdf, .ofx)
│   ├── extractors/               # 8 extratores (nubank x2, c6 x2, itaú, santander, energia, OFX)
│   ├── transform/                # categorizer, normalizer, deduplicator, irpf_tagger (com CNPJ)
│   ├── load/                     # xlsx_writer (8 abas, análise quali/quanti), relatório (MD)
│   ├── integrations/             # Belvo sync, Gmail CSV, docs de MeuPluggy
│   ├── projections/              # cenários financeiros
│   ├── dashboard/                # Streamlit app (8 páginas, Dracula theme)
│   ├── obsidian/                 # Sync com vault Obsidian (frontmatter YAML funcional)
│   └── utils/                    # logger, pdf_reader, file_detector, validator, senhas
│
├── mappings/
│   ├── categorias.yaml           # 111 regras regex
│   ├── overrides.yaml            # Correções manuais
│   ├── metas.yaml                # Metas financeiras
│   └── senhas.yaml               # Senhas PDFs e contas bancárias
│
├── docs/
│   ├── ARCHITECTURE.md           # Diagrama de fluxo ETL
│   ├── ARMADILHAS.md             # Bugs e aprendizados críticos
│   ├── AUDITORIA_SPRINTS.md      # Auditoria sincera de cada sprint
│   ├── MODELOS.md                # Schemas de dados
│   ├── adr/                      # Architecture Decision Records (7)
│   ├── sprints/                  # Documentação de cada sprint (14)
│   └── extractors/               # Auto-documentação de formatos (7)
│
├── scripts/
│   └── pre-commit-check.sh       # ruff + bloqueio de dados sensíveis
│
└── tests/                        # Fixtures sintéticas (Sprint 8)
```

---

## Referências Rápidas

| Recurso | Caminho |
|---------|---------|
| Regras de categorização | `mappings/categorias.yaml` |
| Overrides manuais | `mappings/overrides.yaml` |
| Metas financeiras | `mappings/metas.yaml` |
| Senhas PDFs | `mappings/senhas.yaml` |
| Validador | `python -m src.utils.validator` |
| Pipeline completo | `make process` ou `./run.sh --tudo` |
| Dashboard | `make dashboard` ou `./run.sh --dashboard` |
| Sync Obsidian | `./run.sh --sync` |
| Lint | `make lint` |
| Sprints | `docs/sprints/sprint_NN_*.md` |
| ADRs | `docs/adr/ADR-NN-*.md` |
| Armadilhas | `docs/ARMADILHAS.md` |
| Arquitetura | `docs/ARCHITECTURE.md` |
| Dados faltantes | `DADOS_FALTANTES.md` |
| Automação bancária | `docs/AUTOMACAO_BANCARIA.md` |
| Integrações (Belvo/Gmail) | `src/integrations/README.md` |
| Sync Belvo | `python -m src.integrations.belvo_sync` |
| Download Gmail | `python -m src.integrations.gmail_csv` |

---

## Contexto Ativo -- organizado por Fase do plano 30/60/90

Layout em `docs/sprints/{concluidos,producao,backlog,arquivadas}`. Detalhamento por sprint em cada arquivo `sprint_NN_*.md`. Visão consolidada em `docs/ROADMAP.md`.

### Decisões arquiteturais ativas (ADRs)

Princípios que regem as Fases 1-3 e qualquer decisão futura. Leitura obrigatória antes de propor mudança estrutural.

- **ADR-07** -- Princípio Local First (base histórica)
- **ADR-08** -- Supervisor-Aprovador: Claude propõe, humano aprova, aprovação incorpora regra determinística (implementa Sprints 31 e 34)
- **ADR-09** -- Autossuficiência Progressiva: LLM é ferramenta provisória; métrica-chave é % determinístico (implementa Sprint 36)
- **ADR-10** -- Resiliência a Dados Incompletos: cérebro brilha com gaps; apenas relatório final avisa cobertura parcial (implementa Sprint 21)
- **ADR-11** -- Classificação em Camadas: overrides > regex > supervisor LLM (sugere) > fallback (formaliza pipeline atual)
- **ADR-12** -- Cruzamentos via Grafo de Conhecimento: SQLite + rapidfuzz + entity resolution (implementa Sprint 27a)


- **Concluídas (20):** 01 (MVP), 02 (Infra), 03 (Dashboard v1), 04 (Inteligência), 05 (Relatórios), 06 (Obsidian), 07 (Dashboard v2), 12 (Rebranding), 13 (UI/UX), 14 (Acentuação), 17 (Auditoria), 18 (Dívida Técnica), 19 (Bugs Críticos), 22 (Consolidação), 23 (Verdade nos Dados), 30 (Base Honesta -- testes), 37 (Fix OFX encoding), 38 (Fix deduplicator fuzzy), 39 (Fix IRPF sort), 40 (Fix fallback receita).
- **Fase 1 backlog (30 dias):** 21 (Relatórios Diagnósticos), 30 (Base Honesta + Testes), 31 (Infra LLM + Supervisor Modo 1), 20 (Dashboard Redesign -- mockups primeiro).
- **Fase 2 backlog (60 dias):** 20 (CSS pós-mockups), 32 (OCR Energia via Vision), 33 (Resumo Mensal Narrativo), 34 (Supervisor Modo 2 -- Auditor), 35 (IRPF como YAML), 36 (Métricas IA -- termômetro de autossuficiência).
- **Fase 3 backlog (90 dias):** 27a (Grafo SQLite mínimo), 29a (Busca + Timeline + Pergunte NL), 28 (LLM Orquestrado -- consolidação + ADR-08).
- **Pós-90d backlog:** 24 (Automação Bancária), 25 (Pacote IRPF completo), 27b (Grafo avançado + visualização), 29b (Obsidian rico + MOCs).
- **Arquivadas (7):** 08 (CANCELADA), 09 (ABSORVIDA em 27b), 10 (CANCELADA), 11 (CANCELADA), 15 (ABSORVIDA em 20), 16 (ABSORVIDA em 30), 26 (OBSOLETA -- fundida com 28).
- **Transações:** 2.859 (1.214 histórico + 1.645 dados brutos)
- **Cobertura de meses:** 44 (ago/2022 a out/2026)
- **Bancos:** Itaú, Santander, C6, Nubank (André) + Nubank PF/PJ (Vitória)
- **Categorização:** 100% (111 regras + 10 overrides)
- **IRPF tags:** 79 registros em 5 tipos

### Lacunas conhecidas (auditoria cruzada 2026-04-18)

Auditoria por leitura direta do código -- não confie apenas em sprints antigas.

| Lacuna | Impacto | Fase do plano 30/60/90 |
|--------|---------|------------------------|
| Aba `analise`: texto estático sem diagnóstico | Agora marcada como DEPRECATED; análise real só via LLM narrativo | Fase 2 §2.3 (Sprint 33) |
| Abas `dividas_ativas`/`inventario`/`prazos`: congeladas em 2023 | Marcadas com cabeçalho de snapshot histórico; reabilitação depende de automação bancária | Pós-90d (Sprint 24) |
| Zero infraestrutura LLM | Sem `anthropic` em deps, sem `src/llm/`, sem cache, sem cost_tracker | Fase 1 §1.6 |
| Relatórios mensais são descritivos, não diagnósticos | Listam totais mas não comparam períodos nem sinalizam anomalias | Fase 1 §1.5 |
| Dashboard: layout, tipografia, contraste inconsistentes | Navegação funcional mas visualmente descuidada | Fase 2 §2.1 |
| Sem grafo de conhecimento / entity resolution | Mesmas entidades com nomes diferentes não se cruzam | Fase 3 §3.1 |
| Sem busca global no dashboard | Usuário não consegue rastrear "neoenergia" em todas as transações | Fase 3 §3.2 |
| Download de extratos é 100% manual | Sem integração Open Finance | Fora do escopo do 30/60/90 |
| Sem extrator CAESB/contracheque | Dados faltantes afetam relatório final | Fora do escopo do 30/60/90 |
| Sem agendamento (cron) | Toda execução é on-demand | Fora do escopo do 30/60/90 |

### Mentiras corrigidas nesta revisão

Auditoria identificou afirmações do CLAUDE.md v3.1 que contradiziam o código. Corrigidas:

- **`energia_ocr.py` está registrado no pipeline** (`src/pipeline.py:71-76`). A sprint 23 corrigiu isso antes; a documentação não acompanhou.
- **Obsidian sync gera frontmatter YAML válido** (`src/obsidian/sync.py:114-156`) com `tipo`, `mes`, `receita`, `despesa`, `saldo`, `tags`, `aliases`, `created`. O "frontmatter nulo" que CLAUDE.md mencionava não existe mais.

---

*"O dinheiro é um bom servo, mas um mau mestre." -- Francis Bacon*
