# Sprint 09 -- Testes e CI/CD

## Status: Pendente
Issue: a criar

## Objetivo

Estabelecer infraestrutura de testes automatizados e integração contínua. Garantir que o pipeline seja confiável e mensurável.

## Entregas

- [ ] Fixtures sintéticas (dados financeiros fictícios para todos os formatos)
- [ ] pytest para cada extrator (1 teste mínimo por extrator)
- [ ] pytest para categorizer (regras críticas e edge cases)
- [ ] pytest para deduplicator (3 níveis de dedup)
- [ ] pytest para normalizer
- [ ] Coverage >= 80% em módulos críticos (extractors, transform, utils)
- [ ] GitHub Actions CI (pytest + ruff em push/PR)
- [ ] `./run.sh --check` (health check: dependências, paths, integridade de dados)

## Armadilhas conhecidas

- Fixtures devem ser dados fictícios, nunca dados financeiros reais
- Extratores de PDF precisam de fixtures em PDF (gerar via reportlab ou similar)
- Coverage pode ser artificialmente alta sem testar edge cases reais
- GitHub Actions precisa de tesseract-ocr para testes de OCR

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `tests/conftest.py` | Fixtures compartilhadas |
| `tests/fixtures/` | Dados sintéticos para todos os formatos |
| `tests/test_extractors.py` | Testes de extratores |
| `tests/test_categorizer.py` | Testes do categorizador |
| `tests/test_deduplicator.py` | Testes do deduplicador |
| `tests/test_normalizer.py` | Testes do normalizador |
| `.github/workflows/ci.yml` | Pipeline CI no GitHub Actions |
| `run.sh` | Flag --check adicionada |

## Critério de sucesso

CI verde no GitHub Actions. Coverage >= 80% em módulos críticos. `./run.sh --check` passa sem erros em ambiente limpo.

## Dependências

Nenhuma.
