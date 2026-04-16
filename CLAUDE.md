# CLAUDE.md -- Protocolo Ouroboros

```
VERSÃO: 3.1 | STATUS: PRODUÇÃO (com lacunas documentadas) | LANG: PT-BR
TRANSAÇÕES: 2.859 | MESES: 44 (ago/2022 a out/2026) | BANCOS: 6 | EXTRATORES: 8
SPRINTS CONCLUÍDAS: 14/29 | CATEGORIZAÇÃO: 100% | IRPF TAGS: 79 (14 com CNPJ)
INTEGRAÇÕES: OFX (pronto), Belvo (em teste), Gmail (setup pendente), MeuPluggy (disponível)
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

**AVISO:** Colunas `inss`, `irrf`, `vr_va` estão sempre vazias. O pipeline infere receita das transações bancárias (tipo == "Receita"), mas não tem extrator de contracheque. Sem holerite, esses campos nunca serão preenchidos automaticamente.

| Coluna | Tipo | Preenchido? |
|--------|------|-------------|
| mes_ref | str (YYYY-MM) | sim |
| fonte | str | sim (inferido do banco_origem) |
| bruto | float | sim (valor da transação) |
| inss | float | SEMPRE VAZIO (sem extrator de contracheque) |
| irrf | float | SEMPRE VAZIO (sem extrator de contracheque) |
| vr_va | float | SEMPRE VAZIO (sem extrator de contracheque) |
| liquido | float | sim (= bruto, pois sem deduções) |
| banco | str | sim |

### dividas_ativas

**AVISO:** Dados importados do controle_antigo.xlsx (2022-2023), nunca atualizados. As dívidas reais atuais (Nubank PF/PJ) não estão refletidas. 26 linhas estáticas.

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

**AVISO:** 18 bens importados do histórico, sem mecanismo de atualização. Snapshot congelado.

| Coluna | Tipo |
|--------|------|
| bem | str |
| valor_aquisicao | float |
| vida_util_anos | int |
| depreciacao_anual | float |
| perda_mensal | float |

### prazos

**AVISO:** 6 prazos importados do histórico. Leitura frágil (depende de índices de coluna).

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

**AVISO:** Coluna `cnpj_cpf` está sempre vazia -- o tagger IRPF não extrai CNPJ/CPF do contraparte.

| Coluna | Tipo | Preenchido? |
|--------|------|-------------|
| ano | int | sim |
| tipo | str | sim |
| fonte | str | sim |
| cnpj_cpf | str | SEMPRE VAZIO (sem extração de CNPJ) |
| valor | float | sim |
| mes | str | sim |

### análise

**AVISO:** NÃO contém análise real. Gera frases genéricas com totais ("Total de X transações"). Análise inteligente depende de LLM local (Sprint 08, não implementada).

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
│   ├── obsidian/                 # Sync com vault Obsidian (frontmatter com bug -- Sprint 22)
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

## Contexto Ativo

- **Concluídas:** 1 (MVP), 2 (Infra), 3 (Dashboard v1), 4 (Inteligência), 5 (Relatórios), 6 (Obsidian), 7 (Dashboard v2), 12 (Rebranding), 13 (UI/UX), 14 (Acentuação -- hooks), 17 (Auditoria), 18 (Dívida Técnica), 19 (Bugs Críticos), 23 (Verdade nos Dados -- parcial)
- **Pendentes:** 20 (Dashboard Redesign), 21 (Relatórios Diagnósticos), 22 (Consolidação)
- **Visão:** 24 (Automação Bancária), 25 (Pacote IRPF)
- **Cérebro Inteligente (propostas 2026-04-16):** 26 (Ingestão Universal de Documentos), 27 (Grafo de Conhecimento + Classificação v2), 28 (LLM Orquestrado via Claude Opus), 29 (UX Navegável: busca, timeline, grafo visual, Obsidian rico)
- **Futuro:** 08 (LLM Local -- vira backend alternativo da 28 quando qualidade justificar), 09 (Grafos analíticos Sankey/heatmap -- complementar à 29), 11 (Vault Final), 15 (Dashboard Polish), 16 (Testes CI/CD)
- **Transações:** 2.859 (1.214 histórico + 1.645 dados brutos)
- **Cobertura de meses:** 44 (ago/2022 a out/2026)
- **Bancos:** Itaú, Santander, C6, Nubank (André) + Nubank PF/PJ (Vitória)
- **Categorização:** 100% (111 regras + 10 overrides)
- **IRPF tags:** 79 registros em 5 tipos

### Lacunas conhecidas (auditoria 2026-04-15)

| Lacuna | Impacto | Sprint |
|--------|---------|--------|
| Download de extratos é 100% manual | Sem integração com Open Finance/APIs bancárias | Fora do escopo |
| `health_check.py` não existe | Menu opção 8 e --check crasham | 23 |
| `doc_generator.py` não existe | `make docs` crasha | 23 |
| `energia_ocr.py` não registrado no pipeline | Contas de energia nunca processadas | 23 |
| Obsidian sync com frontmatter nulo | Queries Dataview quebradas | 23 |
| Aba renda: INSS/IRRF/VR-VA vazios | Sem extrator de contracheque | 24 |
| Aba analise: texto estático | Sem LLM (Sprint 08) | 24 | <!-- noqa: accent -->
| Abas dividas/inventario/prazos: congeladas | Dados de 2023, nunca atualizados | 24 |
| Aba irpf: cnpj_cpf vazio | Sem extração de CNPJ | 24 |
| Dashboard: layout, fontes, contraste | Não segue padrões visuais | 21 |
| Relatórios: descritivos, não diagnósticos | Inúteis para análise financeira por IA | 22 |
| Sem agendamento (cron) | Toda execução é on-demand | Fora do escopo |
| Sem extrator CAESB/contracheque | Dados faltantes | Fora do escopo |

---

*"O dinheiro é um bom servo, mas um mau mestre." -- Francis Bacon*
