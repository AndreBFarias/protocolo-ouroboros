---
concluida_em: 2026-04-19
---

# Sprint 14 -- Acentuação, Qualidade e Hooks

## Status: Parcialmente concluída (hooks implementados)
Issue: a criar

## Objetivo

Revisar acentuação em todos os arquivos do projeto, criar hook automático de verificação, e integrar check_gauntlet_freshness (inspirado na Luna).

## Entregas

- [x] Criar hook `scripts/check_acentuacao.py` (dicionário de 50+ palavras comuns sem acento)
- [x] Criar hook `scripts/check_gauntlet_freshness.py` (alerta se gauntlet não rodou há mais de 24h)
- [x] Integrar hooks no `scripts/pre-commit-check.sh`
- [x] Atualizar Makefile: `make lint` inclui verificação de acentuação
- [ ] Revisar acentuação em todos os .py (docstrings, strings, logs, comentários) -- ver Sprint 18
- [ ] Revisar acentuação em todos os .md (docs, sprints, ADRs) -- ver Sprint 18
- [ ] Revisar acentuação em todos os .yaml (categorias, overrides, metas) -- ver Sprint 18

## Conceitos importados

### Da Luna (scripts/hooks/check_acentuacao.py)
- Dicionário de palavras comuns: funcao->função, validacao->validação, descricao->descrição
- Ignora nomes de arquivo e identificadores Python (convenção técnica sem acento)
- T1 blocker: commit falha se encontrar palavra errada em texto livre

### Da Luna (scripts/hooks/check_gauntlet_freshness.py)
- Lê timestamp do GAUNTLET_REPORT.md
- T2 warning se mais de 24h sem rodar gauntlet
- Não bloqueia commit, apenas avisa

## Armadilhas conhecidas

- Identificadores Python devem permanecer sem acento (convenção técnica)
- Texto livre (docstrings, logs, strings de UI, documentação) deve ter acentuação correta
- YAML com acentos precisa de encoding UTF-8 explícito em leitores
- Falsos positivos: "funcao" em importações (ex: `from functools`) não deve ser flagueado

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `scripts/check_acentuacao.py` | Hook de verificação de acentuação |
| `scripts/check_gauntlet_freshness.py` | Hook de freshness do gauntlet |
| `scripts/pre-commit-check.sh` | Integrado com novos hooks |
| `src/**/*.py` | Correção de acentuação em docstrings e strings |
| `docs/**/*.md` | Correção de acentuação em documentação |
| `mappings/*.yaml` | Correção de acentuação em valores de texto |

## Critério de sucesso

Zero palavras em português sem acento em texto livre. Hook bloqueia commits com acentuação incorreta. `make lint` inclui verificação de acentuação. Gauntlet freshness hook funcional.

## Dependências

Nenhuma. Pode ser executada a qualquer momento.
