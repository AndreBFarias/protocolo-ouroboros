# Histórico de Mudanças

Todas as alterações relevantes do projeto estão documentadas aqui.

---

## [Unreleased]

### Added

- **Sprint MOB-bridge-2: geradores de cache JSON para o Mobile.** Pacote
  novo `src/mobile_cache/` com três módulos: `atomic.py`
  (`write_json_atomic` via `.tmp` + `os.replace`), `humor_heatmap.py`
  (cobre 90 dias retroativos lendo `daily/` e `inbox/mente/humor/`,
  agrega células por data+autor, calcula `media_humor_30d`,
  `registros_30d`, `registros_total` por pessoa) e `financas_cache.py`
  (semana ISO atual a partir do XLSX consolidado, `top_categorias` top
  5 com percentual, `delta_textual` heurístico vs média de 12 semanas,
  20 últimas transações). Função `gerar_todos(vault_root, xlsx_path)`
  orquestra ambos. Saídas em `<vault>/.ouroboros/cache/` com
  `schema_version: 1` conforme contrato cruzado da ADR-0012 (Mobile).
  Identidade canônica `pessoa_a`/`pessoa_b`/`casal` em todos os campos
  `autor` (Regra -1). Integrado ao `--full-cycle` no `run.sh` como
  passo final com falha-soft; nova flag `--mobile-cache` standalone
  dispara apenas o gerador. Targets `make sync` (alias de
  `--full-cycle`) e `make mobile-cache` (apenas caches) adicionados.
  33 testes novos cobrindo atomic write, humor heatmap, finanças
  semanais, idempotência e CLI.

### Refactored

- **Sprint MOB-bridge-1: identidade genérica `pessoa_a` / `pessoa_b` no
  backend.** Schema do XLSX (coluna `quem`), normalizer, 5 extratores
  bancários, detector e dashboard passam a operar sobre identificadores
  genéricos. Nomes reais ficam apenas em `mappings/pessoas.yaml`
  (gitignored, campo `display_name`) e são resolvidos em runtime via
  `src.utils.pessoas.nome_de` para apresentação local-first (ADR-24).
  Resolver canônico em `src/utils/pessoas.py` substitui as cópias de
  lógica de identidade espalhadas. XLSX já gerados migrados in-place
  via `scripts/migrar_quem_generico.py` (idempotente, com backup
  automático). `scripts/check_anonimato.sh` adicionado para travar
  regressões. ADR-23 e ADR-24 formalizam a decisão (cruzamento com
  ADR-0011 do companion mobile).

---

## [1.0.1] - 2026-04-15

### Adicionado
- Código de Conduta (Contributor Covenant v2.1)
- Política de Segurança (SECURITY.md)
- Templates de issue e PR para GitHub
- Workflow CI (lint + testes)
- .mailmap para unificação de identidade git
- Badge CI no README

### Corrigido
- Licença MIT corrigida para GPLv3 em pyproject.toml e README
- pyproject.toml modernizado com [build-system], classifiers e URLs

---

## [Sprint 4] - 2026-04-14

### Adicionado
- Sistema de overrides manuais para correção de categorização pós-pipeline
- IRPF tagger automático com 21 regras de classificação fiscal
- 79 transações tagueadas automaticamente para declaração de imposto de renda
- Validador de integridade com 6 checks (totais, categorias, classificações, duplicatas, receita, despesa)

---

## [Sprint 3] - 2026-04-14

### Adicionado
- Dashboard Streamlit interativo com tema dark
- Página de visão geral com métricas consolidadas e gráficos de evolução
- Página de categorias com drill-down por tipo de gasto e classificação
- Página de extrato com filtros dinâmicos e busca textual
- Página de contas fixas com status de pagamento mensal

---

## [Sprint 2] - 2026-04-14

### Adicionado
- Categorização automática 100% funcional com 111 regras regex
- Makefile com alvos padronizados (check, lint, run, install)
- Script pre-commit check para validação antes de commits
- Extrator OCR para contas de energia via Tesseract

### Melhorado
- Cobertura de categorização sem lacunas em transações conhecidas

---

## [Sprint 1] - 2026-04-14

### Adicionado
- Pipeline ETL completo com orquestração via `src/pipeline.py`
- 6 extratores implementados (Itaú PDF, Nubank CSV, C6 CSV, C6 XLS, Santander PDF, Neoenergia OCR)
- 2.859 transações extraídas e processadas
- XLSX final com 8 abas (extrato, renda, dívidas_ativas, inventário, prazos, resumo_mensal, irpf, análise)
- 44 relatórios mensais gerados automaticamente
- Importação de histórico do XLSX antigo (ago/2022 a jul/2023)
- Scaffold completo do projeto (estrutura de pastas, pyproject.toml, install.sh, run.sh)
- Sistema de categorização por regex com mapeamento YAML
- Deduplicação de transferências internas entre contas

---

<!-- "Nós somos o que fazemos repetidamente. Excelência, portanto, não é um ato, mas um hábito." -- Aristóteles -->
