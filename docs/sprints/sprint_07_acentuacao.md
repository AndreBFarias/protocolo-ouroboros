# Sprint 07 -- Acentuação e Qualidade

## Status: Pendente
Issue: a criar

## Objetivo

Revisar acentuação em todos os arquivos do projeto e criar hook automático de verificação para garantir conformidade contínua.

## Entregas

- [ ] Revisar acentuação em todos os .py (docstrings, strings, logs, comentários)
- [ ] Revisar acentuação em todos os .md (docs, sprints, ADRs)
- [ ] Revisar acentuação em todos os .yaml (categorias, overrides, metas)
- [ ] Criar hook scripts/check_acentuacao.py (dicionário de palavras comuns sem acento)
- [ ] Integrar hook no scripts/pre-commit-check.sh

## Armadilhas conhecidas

- Nomes de arquivo e identificadores Python devem permanecer sem acento (convenção técnica)
- Texto livre (docstrings, logs, strings de UI, documentação) deve ter acentuação correta
- YAML com acentos precisa de encoding UTF-8 explícito em leitores

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `scripts/check_acentuacao.py` | Hook de verificação de acentuação |
| `scripts/pre-commit-check.sh` | Integrado com novo hook |
| `src/**/*.py` | Correção de acentuação em docstrings e strings |
| `docs/**/*.md` | Correção de acentuação em documentação |
| `mappings/*.yaml` | Correção de acentuação em valores de texto |

## Critério de sucesso

Zero palavras em português sem acento em texto livre. Hook bloqueia commits com acentuação incorreta. `make lint` inclui verificação de acentuação.

## Dependências

Nenhuma.
