# GSD.md -- Get Stuff Done

Leitura obrigatória antes de qualquer tarefa. Este arquivo resume TUDO que uma IA precisa saber para trabalhar neste projeto sem perder tempo.

---

## Onboarding Rápido (5 passos)

```
1. Ler CLAUDE.md (regras, schema, armadilhas)
2. Ler este GSD.md (contexto, comandos, workflow)
3. Ler a sprint atual em docs/sprints/sprint_NN_*.md
4. Rodar: make process (pipeline completo, valida que tudo funciona)
5. Rodar: python -m src.utils.validator (6 checagens de integridade)
```

Se os passos 4 e 5 passam sem erros críticos, o ambiente está saudável.

---

## Identidade Git

```
Nome: [REDACTED]
Remote SSH: git@github.com-personal:[REDACTED]/protocolo-ouroboros.git
Branch principal: main
Formato commit: tipo: descrição imperativa (PT-BR, sem emojis, sem menção a IA)
Tipos: feat, fix, refactor, docs, test, perf, chore
```

**Atenção:** o push usa SSH alias `github.com-personal`. Se der erro de permissão, verificar `git remote -v`.

---

## Regras Invioláveis (resumo)

1. Acentuação correta em TUDO (código, commits, docs)
2. Zero emojis em qualquer lugar
3. Zero menções a IA em commits
4. Local First (tudo offline, APIs opcionais)
5. Nunca `print()` -- usar logging com rotação
6. Nunca inventar dados
7. `data/` no .gitignore (dados financeiros nunca no repo)
8. Paths relativos via `Path`
9. Citação de filósofo no fim de todo .py

---

## Armadilhas Críticas (top 14)

**Leia ANTES de mexer em qualquer extrator ou no pipeline:**

1. **C6 XLS encriptado** -- `msoffcrypto-tool` decripta, depois `xlrd` lê. Sem msoffcrypto = crash.
2. **Itaú PDF** -- Senha `051273` via `pdfplumber`. Nunca `PyPDF2`.
3. **Nubank 2 formatos** -- Cartão (`date,title,amount`) vs CC (`Data,Valor,Identificador,Descrição`). São extratores SEPARADOS.
4. **Ki-Sabor** -- Mesmo local, 2 categorias por valor: >= R$ 800 = Aluguel, < R$ 800 = Padaria.
5. **Categorizer break vs return** -- `return` após match regex impedia fallback de classificação N/A. Usar `break`.
6. **Histórico corrompido** -- Classificações "Obrigatórios" (com s), "Rou" (truncado). Normalizar no pipeline.
7. **Prazos XLSX antigo** -- Colunas nos índices 2/3, não 0/1. Verificar ambos com fallback.
8. **Git SSH** -- Precisa alias `github.com-personal` no push. Se falhar: `git remote set-url origin git@github.com-personal:[REDACTED]/protocolo-ouroboros.git`
9. **Pre-commit** -- `core.hooksPath` global impede `pre-commit install`. Usar `scripts/pre-commit-check.sh`.
10. **OCR energia** -- Valores R$ 100% OK. Consumo kWh 67% (layout confunde).
11. **Streamlit tabs** -- Troca visual de aba requer JavaScript, não click em elemento.
12. **Santander Black Way** -- É o cartão Elite Visa, final 7342.
13. **Nubank CC duplicatas** -- Arquivos "(1)", "(2)" são cópias. Dedup por UUID essencial.
14. **msoffcrypto-tool** -- Dependência não óbvia. Sem ela, C6 XLS falha silenciosamente.

Detalhes completos em `docs/ARMADILHAS.md`.

---

## Comandos Essenciais

| Comando | O que faz |
|---------|-----------|
| `make help` | Lista todos os targets |
| `make install` | Setup completo (venv + deps + tesseract) |
| `make process` | `./run.sh --tudo` (pipeline completo) |
| `make inbox` | Processa arquivos do inbox |
| `make dashboard` | Abre dashboard Streamlit |
| `make lint` | `ruff check + ruff format --check` |
| `make format` | Formata com ruff |
| `make validate` | `python -m src.utils.validator` |
| `make clean` | Remove caches e logs |
| `./run.sh --mes YYYY-MM` | Processa um mês específico |
| `./run.sh --tudo` | Processa todos os dados |
| `./run.sh --inbox` | Processa inbox |
| `./run.sh --dashboard` | Abre dashboard |
| `./run.sh --sync` | Sincroniza com vault Obsidian |
| `./run.sh --check` | Health check do pipeline |
| `./run.sh --gauntlet` | Executa gauntlet (44 testes, 8 fases) |
| `./run.sh` (sem args) | Menu interativo ANSI colorido |
| `make gauntlet` | Atalho para gauntlet |

---

## Contexto Ativo

### Sprints

| Sprint | Tema | Status |
|--------|------|--------|
| 01 | MVP: Pipeline ETL + 6 extratores + XLSX 8 abas | Concluída (commit 10b4b64) |
| 02 | Infra: Categorização 100%, Makefile, OCR | Concluída (commit 7544101) |
| 03 | Dashboard Streamlit: 6 abas, tema dark | Integrada (commit 9a5bdb5) |
| 04 | Inteligência: overrides, IRPF tagger, validador | Concluída (commit 12b778c) |
| 05 | Relatórios + Projeções: 3 cenários, 7 metas | Integrada |
| 06 | Integração Obsidian: sync, siglas, Dataview | Integrada |
| 08 | Dashboard v2: Redesign Dracula | Concluída (commit f8b1855) |
| 09 | LLM Local: análise financeira via Gemma/Phi | Pendente |
| 10 | Grafos e Visualizações: Sankey, heatmap | Pendente |
| 11 | IRPF Completo: pacote CSV, simulador | Pendente |
| 12 | Vault Final: absorção do CdB pelo Ouroboros | Pendente |
| 13 | Rebranding Protocolo Ouroboros | Concluída (commit b73068a) |
| 14 | UI/UX e Outputs Profissionais | Concluída (commit b73068a) |
| 15 | Acentuação e Qualidade | Pendente |
| 16 | Dashboard Polish Visual | Pendente |
| 17 | Testes e CI/CD | Pendente |
| 18 | Auditoria Final: GitHub-readiness | Pendente |

### Números

- **2.859 transações** (1.214 histórico + 1.645 dados brutos)
- **44 meses** de cobertura (ago/2022 a out/2026)
- **111 regras regex** de categorização + **10 overrides** manuais
- **21 regras IRPF** em 5 tipos de tag -> **79 registros tagueados**
- **6 extratores** funcionais (nubank_cartao, nubank_cc, c6_cc, c6_cartao, itau_pdf, santander_pdf) + **1 OCR** (energia)
- **6 validações** de integridade no validador
- **8 abas** no XLSX de saída
- **44 relatórios** mensais em Markdown
- **44 testes** no gauntlet (8 fases)
- **52 arquivos** sincronizados com vault Obsidian (44 relatórios + 7 metas + 1 MOC)

---

## Checklist Pré-Task

```
- [ ] Li CLAUDE.md e GSD.md
- [ ] Li a sprint que vou trabalhar
- [ ] Li docs/ARMADILHAS.md
- [ ] make lint está passando
- [ ] make process está gerando XLSX sem erros
```

## Checklist Pré-Commit

```
- [ ] make lint (ruff check + format)
- [ ] make process (pipeline completo)
- [ ] python -m src.utils.validator (integridade)
- [ ] Zero emojis no código
- [ ] Zero menções a IA
- [ ] Zero hardcoded values
- [ ] Acentuação correta em todo código novo
- [ ] Commit message PT-BR (tipo: descrição imperativa)
- [ ] Documentação atualizada se necessário
```

---

## Workflow por Tipo de Tarefa

| Tipo | Antes | Validação | Ao concluir |
|------|-------|-----------|-------------|
| Feature | Ler sprint + ARMADILHAS | `make process` + `make validate` | Commit + atualizar sprint doc |
| Bug fix | Reproduzir o bug | Fix + regressão | Commit + issue no GitHub se necessário |
| Extrator novo | Ler docs/extractors/ | Comparar output com dados reais | Commit + criar doc em docs/extractors/ |
| Dashboard | Abrir no browser | Testar todas as páginas visualmente | Commit + screenshot se necessário |
| Docs | Ler existente | Verificar acentuação | Commit |
| Refactor | `make lint` + `make process` | Mesmos outputs que antes | Commit |

---

## Mapeamento de Bancos e Pessoas

### André
- **Itaú**: agência 6450, extrato CC (PDF protegido)
- **Santander**: cartão Elite Visa final 7342 (PDF)
- **C6**: conta corrente (XLSX) + cartão (XLS encriptado)
- **Nubank**: cartão de crédito (CSV)

### Vitória
- **Nubank PF**: conta 97737068-1, CC (CSV com UUID)
- **Nubank PJ**: CNPJ 52.488.753, conta 96470242-3, CC + cartão (CSV)

### Renda
- André: G4F (atual) + Infobase (anterior)
- Vitória: bolsa NEES/UFAL (R$ 3.700, isenta de IR)

---

## Referências Rápidas

| Recurso | Onde |
|---------|-----|
| CLAUDE.md | `./CLAUDE.md` |
| Sprints | `docs/sprints/sprint_NN_*.md` |
| ADRs | `docs/adr/ADR-NN-*.md` |
| Armadilhas | `docs/ARMADILHAS.md` |
| Arquitetura | `docs/ARCHITECTURE.md` |
| Modelos de dados | `docs/MODELOS.md` |
| Auditoria | `docs/AUDITORIA_SPRINTS.md` |
| Dados faltantes | `DADOS_FALTANTES.md` |
| Extratores | `docs/extractors/*.md` |
| Categorias | `mappings/categorias.yaml` |
| Overrides | `mappings/overrides.yaml` |
| Metas | `mappings/metas.yaml` |

---

*"Não é o homem que tem pouco, mas o que deseja mais, que é pobre." -- Sêneca*
