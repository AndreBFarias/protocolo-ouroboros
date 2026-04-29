---
concluida_em: 2026-04-19
---

# Sprint 17 -- Auditoria Final e GitHub-Readiness

## Status: Pendente
Issue: a criar

## Objetivo

Preparar o projeto para compartilhamento público. Sanitizar dados sensíveis, validar todas as funcionalidades e garantir que o repositório está limpo.

## Entregas

- [ ] Sanitização de dados sensíveis (senhas, CPFs, nomes em código)
- [ ] Review de segurança (.gitignore, .env, senhas hardcoded)
- [ ] Validação de todas as funcionalidades (pipeline completo sem erros)
- [ ] Screenshots do dashboard para README
- [ ] Verificar que agentes menores conseguem executar qualquer sprint
- [ ] Lint final completo (ruff + acentuação + segurança)
- [ ] Pipeline completo sem erros em ambiente limpo
- [ ] Validador sem erros críticos

## Armadilhas conhecidas

- Histórico do git pode conter dados sensíveis de commits anteriores
- .env pode ter sido commitado acidentalmente em algum momento
- CLAUDE.md contém senhas de PDFs -- não deve ir pro repositório público
- Screenshots podem conter dados financeiros reais

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `.gitignore` | Revisão final de exclusões |
| `README.md` | Documentação pública do projeto |
| `docs/screenshots/` | Screenshots sanitizados do dashboard |

## Critério de sucesso

Repositório pronto para ser público sem expor dados sensíveis. Pipeline funciona de ponta a ponta em ambiente limpo. Zero alertas críticos no validador.

## Dependências

Todas as sprints anteriores.
