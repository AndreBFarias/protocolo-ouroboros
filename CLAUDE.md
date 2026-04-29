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

### `dividas_ativas`, `inventario`, `prazos`

Snapshots históricos 2022-2023, **não atualizados automaticamente**. Cabeçalho de aviso na linha 1 do XLSX. Reabilitação depende de automação bancária (Sprint 24, pós-90d).

### `resumo_mensal` (gerada automaticamente)

Colunas: mes_ref, receita_total, despesa_total, saldo, top_categoria, top_gasto, total_obrigatorio, total_superfluo, total_questionavel.

### `irpf`

CNPJ/CPF extraídos contextualmente pelo tagger (`src/transform/irpf_tagger.py`). Colunas: ano, tipo, fonte, cnpj_cpf, valor, mes.

### `analise`

Aba viva desde Sprint 53. Visualizações ricas na página "Análise" do dashboard.

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

## Workflow obrigatório

### Antes de implementar
1. Ler `CLAUDE.md` (este arquivo) e `contexto/ESTADO_ATUAL.md`.
2. Ler a sprint atual em `docs/sprints/`.
3. Ler `docs/ARMADILHAS.md` quando relevante.
4. `make lint` para verificar estado atual.

### Ao implementar
1. Manter compatibilidade com pipeline existente.
2. Validar hipótese da spec com `grep` antes de codar.
3. Testar incrementalmente.
4. Verificar acentuação em todo código novo.
5. Nunca quebrar as 8 abas do XLSX.

### Antes de concluir
1. `make lint` (ruff check + format) — exit 0.
2. `make smoke` (8 contratos aritméticos) — 8/8 OK.
3. `pytest tests/ -q` — baseline mantida ou crescida.
4. Verificar dashboard se houver mudanças visuais.
5. Commit com mensagem PT-BR no formato `tipo: descrição imperativa`.

### Anti-migué (gate de "concluído")

Sprint só vira concluída quando:
- Hipótese declarada e validada com grep.
- Proof-of-work runtime-real capturado.
- Quando aplicável: gate 4-way ≥3 amostras (`make conformance-<tipo>`).
- Lint, smoke, pytest verdes.
- Achados colaterais viraram sprint-ID OU Edit-pronto. **Zero "TODO depois".**
- Validador (humano ou subagent) APROVOU.
- Spec movida com frontmatter `concluida_em: YYYY-MM-DD`.

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
| Sprints | `docs/sprints/sprint_NN_*.md` |
| ADRs | `docs/adr/ADR-NN-*.md` |
| Estado atual | `contexto/ESTADO_ATUAL.md` |
| Histórico de sessões | `docs/HISTORICO_SESSOES.md` |

---

*"O dinheiro é um bom servo, mas um mau mestre." — Francis Bacon*
