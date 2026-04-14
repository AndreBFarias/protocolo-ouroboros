# Sprint 09 -- Testes e CI/CD

## Status: Parcialmente coberta pelo gauntlet
Issue: a criar

## Objetivo

Complementar o gauntlet com fixtures PDF/XLS e implementar CI/CD no GitHub Actions. O gauntlet é o sistema primário de testes (inspirado na Luna ADR-13), mas CI precisa de GitHub Actions.

## Contexto

O gauntlet (scripts/gauntlet/) já existe com 8 fases e 44 testes. Esta sprint expande a cobertura e automatiza no CI.

## Entregas

- [ ] Fixtures sintéticas para formatos faltantes:
  - PDF Itaú (gerar via reportlab com transações fictícias)
  - XLS C6 encriptado (gerar via openpyxl + msoffcrypto)
  - PDF Santander (layout multi-coluna fictício)
- [ ] Expandir fase `extratores` do gauntlet (testar Itaú, C6, Santander)
- [ ] Expandir fase `categorias` (testar todas 111 regras vs subset atual de 14)
- [ ] Coverage report: instrumentar gauntlet para medir linhas executadas
- [ ] GitHub Actions CI (.github/workflows/ci.yml):
  - pytest + ruff em push/PR
  - gauntlet como step separado
  - Cache de venv e dependências
  - tesseract-ocr no runner para testes OCR
- [ ] `./run.sh --check` (health check completo)

## Conceitos importados

### Da Luna (ADR-13: Gauntlet único teste)
- Gauntlet é a fonte primária de verdade
- pytest pode complementar mas não substituir
- CI roda gauntlet + lint, não apenas unit tests

### Do Controle_de_Bordo_OS (test structure)
- test_domain/, test_adapters/, test_e2e/ -- separação por camada
- asyncio_mode = auto, mypy --strict

## Armadilhas conhecidas

- Fixtures PDF precisam de reportlab para geração (dependência dev)
- Fixtures XLS encriptadas precisam de msoffcrypto-tool
- GitHub Actions precisa de tesseract-ocr para testes OCR
- Coverage pode ser artificialmente alta sem testar edge cases reais

## Critério de sucesso

CI verde no GitHub Actions. Gauntlet com pelo menos 60 testes (expandido dos 44 atuais). `./run.sh --check` passa sem erros em ambiente limpo.

## Dependências

Nenhuma técnica. O gauntlet já existe como base.
