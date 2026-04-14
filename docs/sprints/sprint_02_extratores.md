# Sprint 02 - Extratores Complementares + Infra Base

## Objetivo

Completar a cobertura de extratores para todos os formatos de arquivo encontrados, implementar auto-documentação dos formatos e estabelecer infraestrutura de qualidade de código.

## Entregas

- [ ] Extrator genérico de conta de energia (Neoenergia via OCR/Moondream)
- [ ] Extrator genérico de conta de água (CAESB)
- [ ] Parser de boleto genérico (extração de valor, vencimento, beneficiário)
- [ ] Auto-documentação de formatos em docs/extractors/ (cada extrator documenta o que espera)
- [ ] Makefile ou Taskfile (comandos padronizados do projeto)
- [ ] Pre-commit hooks: ruff check, ruff format
- [ ] Pre-commit hook: bloqueio de dados financeiros reais no commit

## Dependências

Sprint 1 (MVP funcional com pipeline base e extratores principais).

## Critério de Sucesso

Todos os formatos de arquivo encontrados no inbox possuem extrator funcional. Pre-commit hooks instalados e ativos. Documentação de formatos gerada automaticamente.

## Estimativa de Complexidade

**Média.** OCR para contas de energia adiciona complexidade, mas os demais itens são incrementais. Estimativa: 1.5-2 semanas.
