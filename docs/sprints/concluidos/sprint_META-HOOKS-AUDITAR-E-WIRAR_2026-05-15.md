---
id: META-HOOKS-AUDITAR-E-WIRAR
titulo: Auditar 16 scripts em `hooks/` e wirar/arquivar/deletar
status: concluída
concluida_em: 2026-05-15
prioridade: P1
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 2
origem: auditoria 2026-05-15. `.pre-commit-config.yaml` declara apenas 2 hooks (ruff + `check_dados_financeiros`). Mas `hooks/` contém 17 scripts: check_anonymity, check_citacao_filosofo, check_commit_author, check_commit_msg, check_complexity, check_dados_financeiros, check_diff_anti_burla, check_emojis, check_file_size, check_logger_usage, check_new_prints, check_path_consistency, check_silent_except, pre_push_protect_main, remove_coauthor, sprint_auto_move. 15 estão executáveis mas não wired. Confusão: dev vê 17 scripts mas só 1 roda.
---

# Sprint META-HOOKS-AUDITAR-E-WIRAR

## Contexto

Hooks são primeira linha de defesa: bloqueiam commits com emojis (padrão (c)), com menção a IA (padrão (d)), sem acentuação (padrão (b)), com PII em INFO log (padrão (e)). Quando não-wired, padrões viram declaração honorária.

Cada script em `hooks/` precisa receber um destino claro:
1. **Ativo** (wirar em `.pre-commit-config.yaml` ou git hook nativo)
2. **Coberto por outra rota** (ex: acentuação já roda em `make lint` — hook redundante)
3. **Dead code** (mover para `hooks/_arquivado/`)

## Hipótese e validação ANTES

H1: 16 hooks executáveis sem wiring:

```bash
ls -la hooks/*.{py,sh} | wc -l
# Esperado: 17

grep -E "^\s*-\s+id:|^\s*entry:" .pre-commit-config.yaml | wc -l
# Esperado: ~4 (ruff + format + 1 local)
```

H2: alguns hooks já são executados por outro mecanismo:

```bash
grep -l "check_acentuacao\|check_acentuacao.py" Makefile scripts/
# Esperado: já roda em make lint, não precisa de hook próprio
```

## Objetivo

Para cada um dos 16 hooks, fazer 1 decisão:

| Hook | Decisão proposta | Justificativa |
|---|---|---|
| check_anonymity.py | Wirar em commit-msg | Bloqueia push de PII no log de commit |
| check_citacao_filosofo.py | Wirar em pre-commit (só src/**/*.py) | Padrão (g) cita filosofia |
| check_commit_author.sh | Wirar em commit-msg | Garante autoria |
| check_commit_msg.py | Wirar em commit-msg | Padrão (b/c/d): acentuação, emoji, IA |
| check_complexity.py | Arquivar (over-engineering para pessoal) | Métrica útil só em equipe |
| check_dados_financeiros.py | JÁ ATIVO | nada a fazer |
| check_diff_anti_burla.py | Wirar em pre-commit | Anti-pattern "ressuscitar código deletado" |
| check_emojis.py | Wirar em pre-commit | Padrão (c) |
| check_file_size.py | Arquivar (regra (h) revogada 2026-05-12) | Sem critério |
| check_logger_usage.sh | Wirar em pre-commit (só src/**) | Padrão (e) print proibido |
| check_new_prints.py | Wirar em pre-commit (só src/**) | Padrão (e) |
| check_path_consistency.py | Wirar em pre-commit | Padrão (f) |
| check_silent_except.sh | Wirar em pre-commit | Anti-pattern except: pass |
| pre_push_protect_main.sh | Wirar em pre-push | Bloqueia force-push em main |
| remove_coauthor.sh | Wirar em prepare-commit-msg | Padrão (d) |
| sprint_auto_move.py | Manter manual (script de saída de sprint) | Não é hook, é util |

Implementação:
1. Editar `.pre-commit-config.yaml` adicionando os ativados.
2. Criar `hooks/_arquivado/` e mover `check_complexity.py`, `check_file_size.py`.
3. Renomear `sprint_auto_move.py` → `scripts/sprint_auto_move.py` (não é hook).
4. Atualizar `hooks/README.md` com mapa decisão.

## Não-objetivos

- Não reescrever hooks; só wirar/mover/arquivar.
- Não tocar `.claude/hooks/session-start-projeto.py` (CC nativo).
- Não criar hooks novos (foco em consolidar existentes).

## Proof-of-work runtime-real

```bash
# 1. Hooks wirados rodam em commit teste
echo "# teste" >> /tmp/teste_hook.txt
.venv/bin/pre-commit run --all-files 2>&1 | tail -30
# Esperado: cada hook ativo reporta status

# 2. Arquivados não rodam
ls hooks/_arquivado/
# Esperado: 2 arquivos (check_complexity, check_file_size)

# 3. sprint_auto_move movido
ls scripts/sprint_auto_move.py
# Esperado: exists
ls hooks/sprint_auto_move.py
# Esperado: not exists

# 4. README documenta decisão
grep -c "Decisão:" hooks/README.md
# Esperado: ≥16
```

## Acceptance

- 13 hooks wired ativamente.
- 2 hooks arquivados (com README explicando porque).
- 1 hook movido para scripts/.
- `pre-commit run --all-files` exit 0 num commit limpo.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (n) Defesa em camadas — hooks complementam make lint.
- (l) Achado colateral vira sprint-filha — se algum hook quebrar com commits existentes, sprint dedicada.

---

*"Hook que não roda é regra honorária. Regra honorária é regra que ninguém respeita." — princípio do guarda real*
