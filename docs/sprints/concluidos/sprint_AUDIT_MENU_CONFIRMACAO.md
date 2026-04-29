---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDIT-MENU-CONFIRMACAO
  title: "Flag --sim em run.sh para pular confirmacao quando vindo do menu interativo"
  prioridade: P2
  estimativa: ~45min
  origem: "auditoria externa 2026-04-28 P2-04 -- menu opção 7 chama --reextrair-tudo cuja confirmacao do bash recebe stdin redirecionado e cancela silenciosamente"
  touches:
    - path: run.sh
      reason: "--reextrair-tudo aceita flag --sim que pula confirmar()"
    - path: scripts/menu_interativo.py
      reason: "_acao_auditoria_opus chama _rodar_run_sh('--reextrair-tudo', '--sim') + avisa o usuario antes"
    - path: tests/test_menu_interativo.py
      reason: "regressao: opção 7 invoca run.sh com --sim"
  forbidden:
    - "Mudar comportamento default sem --sim (preserva confirmacao no terminal)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_menu_interativo.py -v"
  acceptance_criteria:
    - "./run.sh --reextrair-tudo --sim pula confirmar() e roda direto"
    - "./run.sh --reextrair-tudo (sem flag) pede confirmacao como antes"
    - "Menu opção 7 imprime aviso de confirmacao automatica antes de delegar"
```

---

# Sprint AUDIT-MENU-CONFIRMACAO

**Status:** BACKLOG (P2, criada 2026-04-28 pela auditoria externa)

## Motivação

`scripts/menu_interativo.py::_acao_auditoria_opus` chama `_rodar_run_sh("--reextrair-tudo")`. O bash internamente chama `confirmar "Tem certeza?"`. Mas o stdin do subprocesso não eh o terminal do usuario -- a confirmacao recebe string vazia, condicao falha, **operação eh cancelada silenciosamente**. O Python recebe rc=0 e o usuario pensa que rodou.

## Implementação

### `run.sh`

```bash
--reextrair-tudo)
    msg_aviso "Reextracao em lote: vai limpar nodes 'documento' do grafo."
    if [[ "${2:-}" == "--sim" ]] || confirmar "Tem certeza? (operação irreversivel)"; then
        msg_info "Rodando automacoes de cleanup..."
        run_passo "dedup_classificar" python -m scripts.dedup_classificar_lote --executar
        ...
        python -m scripts.reprocessar_documentos --forcar-reextracao
    fi
    ;;
```

### `menu_interativo.py`

```python
def _acao_auditoria_opus() -> bool:
    cons = _console()
    cons.print("[red]ATENCAO: vai limpar 'documento' do grafo e re-ingerir tudo.[/]")
    if not _confirmar_console(cons, "Confirma? (s/N)"):
        return False
    cons.print("[magenta]Auditoria Opus completa: rodando com --sim[/]")
    rc = _rodar_run_sh("--reextrair-tudo", "--sim")
    return rc == 0
```

Confirmacao acontece UMA VEZ no Python (com TTY garantido). Bash recebe `--sim` e não confirma de novo.

## Testes regressivos

1. `./run.sh --reextrair-tudo --sim` (mock pipeline) -> roda sem prompt.
2. `./run.sh --reextrair-tudo` sem flag -> pede confirmacao.
3. Menu opção 7 com input "n" -> não roda subprocess.
4. Menu opção 7 com input "s" -> roda com --sim.
