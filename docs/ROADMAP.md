# Roadmap -- Protocolo Ouroboros

```
VERSÃO: 3.0 | SPRINTS: 14 | CONCLUÍDAS: 6/14
ÚLTIMA ATUALIZAÇÃO: 2026-04-14
```

---

## Visão

Sistema de inteligência financeira pessoal para o casal André e Vitória. Pipeline ETL que centraliza dados bancários de múltiplas fontes em XLSX consolidado + dashboard Streamlit + relatórios mensais + integração Obsidian.

**Evolução futura:** unificar com o Controle_de_Bordo_OS (arquitetura hexagonal, Pydantic, SQLite+WAL, event bus) e o vault Obsidian (1.202 notas, PARA method) em um único ecossistema de gestão de vida.

---

## Sprints Concluídas

### Sprint 01 -- MVP Pipeline ETL
**Commit:** `10b4b64` | **Issue:** #1

Pipeline completo: 6 extratores (Nubank cartão, Nubank CC, C6, Itaú PDF, Santander PDF, energia OCR), categorização regex, XLSX 8 abas. Scaffold do projeto com estrutura `src/`, `data/`, `mappings/`.

### Sprint 02 -- Infra de Qualidade
**Commit:** `7544101` | **Issue:** #2

Categorização 100% (111 regras regex + 10 overrides), Makefile com 13 targets, pre-commit hooks, auto-documentação de formatos em `docs/extractors/`, extrator de energia via OCR (Tesseract).

### Sprint 03 -- Dashboard Streamlit v1
**Commit:** `9a5bdb5` | **Issue:** #3

Dashboard interativo com 6 abas (Visão Geral, Categorias, Extrato, Contas, Projeções, Metas), sidebar com filtros globais (mês, pessoa), tema dark mode, gráficos Plotly. Auditoria visual via Chrome MCP.

Correções aplicadas:
- Abas do menu superior visíveis com CSS personalizado (dark mode)
- Donut chart com `textposition="inside"` para fatias pequenas
- Botão "Exportar CSV" visível em dark mode (CSS override)

### Sprint 04 -- Inteligência de Categorização
**Commit:** `12b778c` | **Issue:** #4

Overrides manuais (`mappings/overrides.yaml`), IRPF tagger automático (21 regras, 5 tipos, 79 registros), validador de integridade (6 checagens), deduplicação 3 níveis (UUID, hash fuzzy, pares de transferência).

### Sprint 05 -- Relatórios e Projeções
**Issue:** #5

Relatório mensal automático em Markdown, projetor de 3 cenários (Ritmo Atual, Pós-Infobase, Meta Apartamento), página Metas com 7 metas (5 monetárias + 2 binárias), timeline de prazos, simulação personalizada com slider.

Correções aplicadas:
- 7 metas visíveis com contagem no topo
- Barra de progresso 0% visível (mínimo 1% visual)
- Nota explicativa no cenário negativo Pós-Infobase
- Cálculo unificado: `relatorio.py` importa `_calcular_medias()` de `scenarios.py`

### Sprint 06 -- Integração Obsidian
**Issue:** #6

Sync automático de 44 relatórios + 7 metas + 1 MOC para o vault `~/Controle de Bordo/`. Frontmatter YAML compatível com Dataview, backlinks entre relatórios e metas.

Correções aplicadas:
- Idempotência total: campo `created` preservado em reexecuções
- Siglas preservadas: `_formatar_nome()` mantém PF, PJ, CNH (não "Pf", "Pj")
- Preposições em minúsculas: "de", "da", "do" (não "De", "Da")

---

## Infraestrutura Transversal

### Menu Interativo (`run.sh`)
Menu ANSI colorido com banner box-drawing, 9 opções numeradas, subprompts para mês/ano, contagem de transações do XLSX. Inspirado no `run_luna.sh` do projeto Luna.

### Gauntlet (Sistema de Testes)
44 testes em 8 fases (extratores, categorias, dedup, xlsx, relatório, projeções, obsidian, dashboard). Fixtures sintéticas, diretórios temporários, relatório GAUNTLET_REPORT.md. Inspirado na ADR-13 da Luna (gauntlet como único sistema de testes).

---

## Sprints Pendentes

### Sprint 07 -- Acentuação e Qualidade
**Dependências:** Nenhuma

Revisar acentuação em todos os arquivos (.py, .md, .yaml). Criar hooks pre-commit: `check_acentuacao.py` (dicionário de 50+ palavras) e `check_gauntlet_freshness.py` (alerta se gauntlet não rodou há 24h). Conceitos da Luna: hooks como T1 blockers e T2 warnings.

### Sprint 08 -- Dashboard v2
**Dependências:** Sprint 03

Redesign visual completo. Melhorar contraste de cards (#252840 ou borda sutil), responsividade em resoluções menores, gráficos avançados (Sankey de fluxo financeiro, heatmap de gastos estilo GitHub).

### Sprint 09 -- Testes e CI/CD
**Dependências:** Gauntlet existente

Fixtures sintéticas para formatos faltantes (PDF Itaú, XLS C6 encriptado, PDF Santander). Expandir gauntlet para 60+ testes. GitHub Actions CI (gauntlet + ruff em push/PR). Coverage report. Conceitos do Controle_de_Bordo_OS: `test_domain/`, `test_adapters/`, `test_e2e/`.

### Sprint 10 -- LLM Local
**Dependências:** Sprint 05

Módulo `src/analysis/llm_analyst.py` com modelo local (Gemma 2B ou Phi-3 Mini, RTX 3050 4GB VRAM). Insights automáticos no relatório ("delivery subiu 30%"). Fallback sem GPU: análise baseada em regras. Pipeline nunca falha por falta de LLM.

### Sprint 11 -- Grafos e Visualizações
**Dependências:** Sprint 05 + Sprint 10

Sankey diagram de fluxo financeiro (de onde vem, pra onde vai cada real). Grafo de dependência entre metas (networkx). Heatmap de gastos (calendário estilo GitHub). Trend analysis com média móvel 3 meses.

### Sprint 12 -- IRPF Completo
**Dependências:** Sprint 04

Gerador de pacote IRPF (`./run.sh --irpf YYYY`): CSVs por tipo, simulador completo vs simplificado, checklist de documentos, página Streamlit dedicada.

### Sprint 13 -- Integração Vault Final
**Dependências:** Todas anteriores

Decisão arquitetural: mover projeto pro vault vs vault pro projeto vs manter separados. Se unificar: migrar XLSX para SQLite+WAL, adotar Pydantic models, implementar event bus tipado, unificar CLI (bash -> Typer).

Conceitos do Controle_de_Bordo_OS:
- **Arquitetura hexagonal**: domain/ nunca importa adapters/
- **Pydantic Models**: Transaction com validação tipada
- **SQLite+WAL**: Storage ACID, queries SQL
- **Event Bus**: pub/sub tipado para pipeline
- **4-Phase Migration**: JSON_ONLY -> DUAL_WRITE -> DUAL_READ_SQL -> SQLITE_ONLY

Conceitos do vault Obsidian:
- **PARA method**: Projects, Areas, Resources, Archive
- **Dataview queries**: agregação automática
- **MOC**: Map of Content como hub de navegação

### Sprint 14 -- Auditoria Final
**Dependências:** Sprint 13

GitHub-readiness: README.md público, screenshots, badges CI, documentação completa. Verificação de .gitignore (dados sensíveis), limpeza de código morto, revisão de acentuação final.

---

## Ecossistema de 3 Projetos

| Projeto | Caminho | Descrição |
|---------|---------|-----------|
| **Protocolo Ouroboros** (este) | `~/Desenvolvimento/protocolo-ouroboros` | Pipeline ETL financeiro maduro, 38 arquivos Python |
| **Controle_de_Bordo_OS** | `~/Desenvolvimento/Controle_de_Bordo_OS` | Blueprint arquitetural hexagonal, 20 sprints planejadas |
| **Vault Obsidian** | `~/Controle de Bordo` | 1.202 notas, 24 plugins, organização PARA |

A Sprint 13 avaliará a melhor estratégia de unificação.

---

## Priorização

```
Sprint 01-06  ████████ Concluídas (MVP -> Dashboard -> Obsidian)
Sprint 07     ██████── Acentuação (qualidade, pode rodar a qualquer momento)
Sprint 08     █████─── Dashboard v2 (visual polish)
Sprint 09     █████─── Testes e CI (estabilidade)
Sprint 10     ████──── LLM Local (insights automáticos)
Sprint 11     ███───── Grafos e viz avançada
Sprint 12     ███───── IRPF completo
Sprint 13     ██────── Integração vault (decisão arquitetural)
Sprint 14     █─────── Auditoria final (GitHub-readiness)
```

---

*"Um sistema inteligente não é o que faz tudo. É o que sabe o que fazer primeiro."*
