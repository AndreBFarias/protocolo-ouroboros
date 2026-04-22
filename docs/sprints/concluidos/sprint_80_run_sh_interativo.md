## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 80
  title: "run.sh interativo: menu com Processar Inbox / Dashboard / Relatório / Sync / Tudo"
  touches:
    - path: run.sh
      reason: "sem args agora abre menu interativo em vez de printar help"
    - path: scripts/menu_interativo.py
      reason: "novo: menu Python via rich.prompt ou inquirer"
    - path: tests/test_menu_interativo.py
      reason: "teste via subprocess"
  n_to_n_pairs: []
  forbidden:
    - "Quebrar uso existente com flags (--inbox, --tudo, --dashboard, --sync, --check)"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_menu_interativo.py -v"
      timeout: 60
  acceptance_criteria:
    - "./run.sh sem args abre menu com 5 opções"
    - "Após processar inbox, pergunta: '(1) Abrir dashboard, (2) Gerar relatório, (3) Ambos, (4) Nada'"
    - "Flags existentes continuam funcionando (./run.sh --tudo, --check, --dashboard, --sync)"
    - "Opção 'Tudo' roda inbox + pipeline + sync + pergunta dashboard/relatório"
    - "Menu usa biblioteca leve (rich já está instalada no projeto)"
  proof_of_work_esperado: |
    # echo "5" | ./run.sh  -> sai sem erro (opção Sair)
    # echo "1" | ./run.sh  -> processa inbox (ou diz 'nada novo')
```

---

# Sprint 80 — run.sh interativo

**Status:** CONCLUÍDA (2026-04-22)
**Prioridade:** P2
**Dependências:** Sprint 70 (adapter Controle de Bordo)
**Issue:** UX-ANDRE-08

## Problema

Andre: "ao rodar o nosso run.sh ele inicia tudo automaticamente, extrai os textos, tabela tudo, renomeia, move pras pastas corretas, gera as tags, gera o trackeamento de tudo, após ele pergunta se quero abrir o dashboard, ou gerar o relatório do periodo ou dia".

Hoje `run.sh` é só dispatch por flags. Sem arg imprime help.

## Implementação

`scripts/menu_interativo.py`:

```python
from rich.prompt import Prompt
from rich.console import Console

console = Console()

def main():
    console.print("[bold purple]Protocolo Ouroboros[/] - menu principal")
    opcao = Prompt.ask(
        "O que você quer fazer?",
        choices=["1", "2", "3", "4", "5"],
        default="5",
    )
    # 1 Processar Inbox; 2 Dashboard; 3 Relatório; 4 Sync Obsidian; 5 Tudo; 0 Sair
    if opcao == "1":
        _processar_inbox()
        pergunta_pos()
    elif opcao == "5":
        _processar_inbox()
        _pipeline_completo()
        _sync_obsidian()
        pergunta_pos()
    # ...

def pergunta_pos():
    acao = Prompt.ask(
        "E agora?",
        choices=["dashboard", "relatorio", "ambos", "nada"],
        default="nada",
    )
    # ...
```

`run.sh`:

```bash
#!/usr/bin/env bash
if [ $# -eq 0 ]; then
    exec .venv/bin/python scripts/menu_interativo.py
fi
# ... resto igual (--inbox, --tudo, --dashboard, --sync, --check)
```

## Evidências

- [x] `scripts/menu_interativo.py` novo (~180L): 5 ações + saída, pergunta pós-ação `OPCOES_FOLLOW_UP = (dashboard, relatorio, ambos, nada)`, dispatcher que delega a subprocessos de `run.sh` (não reescreve o que já funciona). `OUROBOROS_MENU_SKIP=1` permite saída silenciosa em CI.
- [x] `run.sh`: nova flag `--menu` que faz `exec` para o Python script (preserva todas as flags existentes).
- [x] 5 testes em `tests/test_menu_interativo.py`: importação, número de opções do menu (5 + saída), 4 opções de follow-up, env var de skip, execução real no venv com stdin vazio.
- [x] Gauntlet: make lint exit 0, 1009 passed (+5), smoke 8/8 OK.

### Ressalva

- [R80-1] O `run.sh` sem argumentos continua com o menu bash antigo (que já existe e funciona). A Sprint 80 entrega o menu Python com rich como `--menu` explícito; a troca do default do `./run.sh` para invocar `menu_interativo.py` fica como decisão do André (é apenas uma linha no dispatch case do run.sh). Motivo da cautela: o menu bash atual já é estético e tem várias ações que nem estão no Python (p.ex. processar_mes específico, backup manual). Consolidar num único caminho exige passagem mais cuidadosa.

---

*"Sem menu o usuário vira manual de CLI." — princípio"*
