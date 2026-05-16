---
id: META-LIMPEZA-SILENT-EXCEPT
titulo: Limpar 34 violações de `except: pass` em `src/` detectadas por `check_silent_except.sh`
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de:
  - META-HOOKS-AUDITAR-E-WIRAR (concluída — wirou o hook que detectou)
esforco_estimado_horas: 2
origem: achado colateral da sprint META-HOOKS-AUDITAR-E-WIRAR (executor `af13dd9f`, 2026-05-15). Wirar `check_silent_except.sh` no pre-commit revelou 34 ocorrências pré-existentes de `except: pass` (ou variantes silenciosas) em `src/`. Hook foi configurado com `files: ^src/.*\.py$` para rodar só em diffs de src/ — dívida histórica não bloqueia commits que não tocam src/.
---

# Sprint META-LIMPEZA-SILENT-EXCEPT

## Contexto

Padrão `except: pass` silencia erros silenciosamente — anti-padrão proibido no projeto (padrão `(e)` "Nunca inventar dados"). Cada ocorrência merece decisão consciente: (a) logar via `logger.exception()` e re-raise se erro real; (b) logar como warning e continuar se erro esperado (ex: arquivo opcional ausente); (c) suprimir explicitamente com `# noqa: BLE001` ou similar + comentário justificando.

## Hipótese e validação ANTES

```bash
grep -rln "except:\s*$\|except.*:\s*pass\|except Exception.*:\s*pass" src/ | head -20
# Esperado: ≥34 ocorrências

bash hooks/check_silent_except.sh --all-src 2>&1 | head -20
# Esperado: lista 34 paths
```

## Objetivo

Para cada uma das 34 ocorrências:
1. Ler contexto (qual erro está sendo capturado).
2. Decidir entre 3 opções (logar+re-raise, logar warning, suprimir explícito).
3. Aplicar Edit cirúrgico.
4. Validar pytest no módulo tocado continua verde.

Dividir em ondas de ~10 ocorrências por commit para facilitar revisão.

## Não-objetivos

- Não mudar comportamento funcional (apenas tornar erro visível).
- Não tocar testes (`tests/**`) — foco em `src/**`.
- Não tocar arquivos do escopo de outras sprints em andamento.

## Proof-of-work runtime-real

```bash
bash hooks/check_silent_except.sh --all-src
# Esperado: exit 0 ou ≤5 ocorrências restantes (com noqa documentado)

.venv/bin/pytest tests/ -q --tb=no
# Esperado: baseline mantida
```

## Acceptance

- ≤5 `except: pass` restantes em `src/`, cada um com `# noqa: BLE001 -- <razão>`.
- Pytest > 3046 (manteve baseline).
- Lint exit 0. Smoke 10/10.

## Padrões aplicáveis

- (e) Nunca inventar dados (erro silenciado é mentira).
- (a) Edit incremental.

---

*"Erro escondido cresce na sombra; erro logado encontra remédio." — princípio da exception visível*
