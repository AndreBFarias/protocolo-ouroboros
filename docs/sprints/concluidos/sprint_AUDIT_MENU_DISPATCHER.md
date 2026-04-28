## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDIT-MENU-DISPATCHER
  title: "Mapear '0' explicitamente em _DISPATCHER ou usar match/case"
  prioridade: P3
  estimativa: ~20min
  origem: "auditoria externa 2026-04-28 P3-04 -- OPCOES_MENU declara '0': 'Sair' mas _DISPATCHER não mapeia '0', design fragil"
  touches:
    - path: scripts/menu_interativo.py
      reason: "executar_menu trata '0' antes de dispatch -- proteger contra novos contributors"
  forbidden:
    - "Mudar comportamento atual da opção '0' (sair)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_menu_interativo.py -v"
  acceptance_criteria:
    - "_DISPATCHER tem chave '0' mapeada para lambda/funcao explicita _acao_sair"
    - "Adicionar nova opção no menu não quebra fluxo de saida"
```

---

# Sprint AUDIT-MENU-DISPATCHER

**Status:** BACKLOG (P3, criada 2026-04-28 pela auditoria externa)

## Motivação

`OPCOES_MENU` lista `"0": "Sair"`. `Prompt.ask(choices=list(OPCOES_MENU.keys()))` aceita "0". Mas `_DISPATCHER` so tem `"R", "1"-"7"`. O fluxo `executar_menu` trata "0" via `if escolha == "0"` antes de `acao = _DISPATCHER[escolha]`. Funciona, mas eh fragil:

```python
# Se algum dia alguem fizer:
acao = _DISPATCHER.get(escolha) or (lambda: 0)
# ou
acao = _DISPATCHER[escolha]
# ...sem o early-return de "0" -- KeyError.
```

## Implementação

```python
def _acao_sair() -> bool:
    """Sentinela: indica para executar_menu encerrar o loop."""
    _console().print("[dim]Encerrando.[/]")
    return True  # 'disruptiva' para não perguntar follow-up


_DISPATCHER: dict[str, callable] = {
    "R": _acao_rota_completa,
    "1": _acao_inbox,
    "2": _acao_dashboard,
    "3": _acao_relatorio,
    "4": _acao_sync,
    "5": _acao_tudo,
    "6": _acao_reextrair,
    "7": _acao_auditoria_opus,
    "0": _acao_sair,  # NOVO
}
```

`executar_menu` ainda detecta "0" pelo retorno e não pergunta follow-up.

## Testes regressivos

- `_DISPATCHER` tem todas as chaves de `OPCOES_MENU`.
- `_acao_sair()` retorna `True` para evitar follow-up question.
- Menu com input "0" sai com rc=0.
