# Histórico de Mudanças

Todas as alterações relevantes do projeto estão documentadas aqui.

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
