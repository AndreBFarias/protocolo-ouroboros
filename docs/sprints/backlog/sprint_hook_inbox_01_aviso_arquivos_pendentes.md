# Sprint HOOK-INBOX-01 -- Hook contador de arquivos pendentes no inbox

> **Slug ASCII para referência cruzada**: `hook_inbox_01`. Em texto livre, usar "HOOK-INBOX-01".

**Origem**: prompt complementar do dono em 2026-04-29 (Gap 3 da sequência D7-extendida).
**Prioridade**: P2 (qualidade de vida).
**Onda**: 1 (anti-débito + qualidade)
**Esforço estimado**: 1h
**Depende de**: nada -- pode rodar antes ou depois de VALIDAR-BATCH-01. Recomendado: depois (hook pode citar a skill).

## Problema

Princípio D7 ("nada bloqueia, tudo é visível") quebra silenciosamente quando arquivos esquecidos acumulam em `data/inbox/`. Não há feedback proativo se há fila pendente. Inbox com 30 arquivos não-processados há 2 meses é incompatível com cobertura observável.

## Hipótese

Claude Code tem mecanismo de hooks (`.claude/hooks.json`) que dispara em eventos como `PreToolUse` e `UserPromptSubmit`. Posso criar hook leve que conta arquivos em `data/inbox/` quando detecta comandos relacionados (ex: `./run.sh --inbox`, `--tudo`, `--full-cycle`) e imprime aviso amarelo se ≥ N. Aviso, não bloqueio (D7 não-gate).

**Validar antes de codar**:
- `ls .claude/hooks.json` -- atualmente NÃO EXISTE (verificado 2026-04-29).
- `cat .claude/settings.local.json` -- só permissions, nenhum hook.
- Verificar se Claude Code reconhece hooks no path `.claude/hooks.json` ou `.claude/hooks/` -- consultar docs oficiais via guide claude-code se necessário.
- Confirmar que `data/inbox/` pode não existir (visto em 2026-04-29: ausente em fresh state).

## Implementação proposta

### Etapa 1 -- Script contador (~20min)

`scripts/contar_inbox_pendentes.py`:

```python
"""Conta arquivos pendentes em data/inbox/ e imprime aviso se >= threshold.

Uso: invocado por hook .claude/hooks.json quando dono digita
./run.sh --inbox/--tudo/--full-cycle.

Saida (stderr, codigo 0 sempre -- D7 nao-gate):
  - 0 arquivos: silencio absoluto.
  - 1..N-1: silencio (configuravel).
  - >= N: aviso amarelo "INBOX: X arquivo(s) pendente(s)..."

Configuracao:
  OUROBOROS_INBOX_THRESHOLD=N  (default 1)
  OUROBOROS_AUTO_HINT_INBOX=0  (desativa)
"""
```

Trata `data/inbox/` ausente como 0 arquivos (silencioso).

### Etapa 2 -- Hook em `.claude/hooks.json` (~20min)

Estrutura proposta (a confirmar com docs oficiais):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": {"tool": "Bash", "pattern": "run\\.sh\\s+--(inbox|tudo|full-cycle)"},
        "command": "python /home/andrefarias/Desenvolvimento/protocolo-ouroboros/scripts/contar_inbox_pendentes.py"
      }
    ]
  }
}
```

Comportamento:
- Hook roda ANTES do comando real.
- Script imprime aviso em stderr (não polui stdout).
- Exit code 0 sempre (D7 não-gate).

### Decisão pendente do dono (modo learning, 5-10 linhas decisivas)

Duas escolhas afetam comportamento -- 5-10 linhas no `.env` ou config decidem:

**A. Threshold de aviso**:
- `OUROBOROS_INBOX_THRESHOLD=1` -- avisa SEMPRE que há arquivo. Ruidoso mas seguro.
- `OUROBOROS_INBOX_THRESHOLD=3` -- avisa só com fila pequena.
- `OUROBOROS_INBOX_THRESHOLD=10` -- avisa só com acúmulo real.

**B. Tipo de hook**:
- `PreToolUse` em Bash com pattern `run\.sh\s+--(inbox|tudo|full-cycle)` -- preciso, dispara só em comandos relevantes.
- `UserPromptSubmit` detectando palavras-chave ("inbox", "processar arquivos") -- abrangente, mas pode disparar em conversa sobre o tema sem comando real.

Default proposto:
- Threshold = **1** (D7 prefere ruído visível sobre fila invisível).
- Tipo = **PreToolUse Bash com pattern** (preciso, sem falso-positivo).

### Etapa 3 -- Testes do script (~10min)

`tests/test_contar_inbox_pendentes.py`:

1. `test_inbox_ausente_retorna_zero_silencioso` (sem `data/inbox/`).
2. `test_inbox_vazio_silencio_absoluto`.
3. `test_threshold_default_um_dispara_com_um_arquivo`.
4. `test_threshold_dez_silencia_ate_nove`.
5. `test_env_var_desativa_aviso` (`OUROBOROS_AUTO_HINT_INBOX=0` -> silêncio).
6. `test_exit_code_sempre_zero` (D7 não-gate).

### Etapa 4 -- Documentação (~10min)

Adicionar seção em `CLAUDE.md` "Workflow obrigatório" mencionando que:
- Hook é configurável via env vars.
- Para desativar em CI: `OUROBOROS_AUTO_HINT_INBOX=0`.
- Aviso aparece em stderr (não atrapalha stdout do pipeline).

## Proof-of-work (runtime real)

```
$ touch data/inbox/teste1.pdf data/inbox/teste2.pdf data/inbox/teste3.pdf
$ ./run.sh --inbox
[INBOX] 3 arquivo(s) pendente(s) em data/inbox/. Considere /validar-inbox antes de prosseguir.
[pipeline] processando data/inbox/...
[...]
$ rm data/inbox/teste*.pdf
$ ./run.sh --inbox
[pipeline] data/inbox/ vazio.
```

## Acceptance criteria

- `scripts/contar_inbox_pendentes.py` criado.
- `.claude/hooks.json` criado com matcher correto.
- Decisões A e B revisadas pelo dono antes de implementar.
- 6 testes passando.
- Docs atualizadas em `CLAUDE.md` com seção "Hooks ativos".
- `make lint` exit 0, `make smoke` 10/10.
- Proof-of-work runtime em commit body.

## Gate anti-migué

(9 checks padrão.)

## Não-objetivos

- **Não fazer**: bloquear pipeline (D7 não-gate).
- **Não fazer**: hook chamar Anthropic API (ADR-13).
- **Não fazer**: tocar em `validacao_csv.py`.
- **Não fazer**: hook em UserPromptSubmit antes de validar com docs oficiais (risco falso-positivo alto).

---

*"Visibilidade proativa, sem fricção."*
