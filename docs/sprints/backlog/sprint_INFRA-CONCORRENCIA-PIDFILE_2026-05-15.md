---
id: INFRA-CONCORRENCIA-PIDFILE
titulo: Lockfile concorrência (fcntl) + toast no dashboard
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-15
fase: PRODUCAO_READY
epico: 2
depende_de: []
esforco_estimado_horas: 3
origem: auditoria 2026-05-15. `./run.sh --tudo` + `make dashboard` simultâneos não têm coordenação. SQLite WAL mitiga grafo mas XLSX em escrita via openpyxl pode corromper. Nenhum `fcntl` ou PIDfile em `run.sh` ou `src/pipeline.py`.
---

# Sprint INFRA-CONCORRENCIA-PIDFILE

## Contexto

Dois cenários reais de concorrência:

1. **Dono roda `./run.sh --tudo` enquanto dashboard está aberto** — dashboard lê grafo + XLSX mid-escrita. Resultado: KPIs incompletos, alerta de "arquivo corrompido" no openpyxl.
2. **Cron/hook dispara `--inbox` enquanto dono roda `--full-cycle` manual** — 2 pipelines escrevendo grafo. SQLite WAL evita corrupção mas dedup pode produzir duplicatas.

Hoje não há lockfile. Detecção de concorrência depende de sorte.

## Hipótese e validação ANTES

H1: nenhum lockfile no projeto:

```bash
grep -rln "fcntl\|flock\|PIDfile\|pid_file" src/ run.sh scripts/
# Esperado: 0 hits (ou só em testes)
```

H2: openpyxl crasha em XLSX semi-escrito (já visto em sessão 2026-05-12):

```bash
grep -A 3 "openpyxl.*BadZipFile\|file is not a zip\|exception openpyxl" logs/*.log 2>/dev/null | head -10
# Esperado: ≥1 hit histórico
```

## Objetivo

1. Criar `src/utils/lockfile.py` com classe `Lockfile`:
   ```python
   class Lockfile:
       def __init__(self, path: Path, descricao: str): ...
       def __enter__(self): ...  # fcntl.flock LOCK_EX | LOCK_NB
       def __exit__(self, *a): ...  # release
   ```
2. Usar em `src/pipeline.py::executar()` — lock em `data/.pipeline.lock` antes do backup. Se já está locked, log error + exit 1.
3. Usar em `run.sh` antes de qualquer pipeline (flock + PID escrito):
   ```bash
   exec 200>/path/to/.run.lock
   if ! flock -n 200; then
       echo "Outra instância do pipeline está rodando (PID $(cat .run.pid))."
       exit 1
   fi
   echo $$ > .run.pid
   ```
4. Dashboard `src/dashboard/app.py` lê PIDfile:
   - Se lock ativo: `st.toast("Pipeline rodando em background. Dados podem estar obsoletos.", icon=":material/sync:")` no topo.
   - Render normal com refresh button.
5. `make check` valida ausência de lock órfão (PID que não responde).

## Não-objetivos

- Não bloquear leitura concorrente (só escrita simultânea).
- Não criar fila de execuções (concorrente = exit 1, não enfileira).
- Não tocar dashboard `pyvis` ou similares (foco em escrita de XLSX/grafo).

## Proof-of-work runtime-real

```bash
# 1. Lock funciona
.venv/bin/python -c "
from src.utils.lockfile import Lockfile
from pathlib import Path
lock = Path('/tmp/teste.lock')
with Lockfile(lock, 'teste'):
    import subprocess
    r = subprocess.run(['python', '-c', '''
from src.utils.lockfile import Lockfile
from pathlib import Path
try:
    with Lockfile(Path(\"/tmp/teste.lock\"), \"teste\"):
        print(\"NAO DEVERIA ENTRAR\")
except BlockingIOError:
    print(\"OK lock funciona\")
'''], capture_output=True, text=True)
    assert 'OK lock funciona' in r.stdout, r.stdout
print('OK concorrencia bloqueada')
"

# 2. Dashboard mostra toast (UI manual)
make dashboard &
sleep 3
./run.sh --inbox &
sleep 2
# Olhar dashboard: deve aparecer toast "Pipeline rodando"
kill %1 %2 2>/dev/null
```

## Acceptance

- `src/utils/lockfile.py` criado com 6 testes.
- `pipeline.py::executar()` envolto em Lockfile.
- `run.sh` com flock guard.
- Dashboard detecta lock e exibe toast.
- 2 instâncias paralelas: uma vence, outra exit 1.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (n) Defesa em camadas — lock em Python (Lockfile) + Bash (flock).
- (e) PII never in INFO log — PID + descrição vão pro log, dados financeiros nunca.

---

*"Duas mãos no mesmo tear desfazem o tecido." — princípio da serialização de escritas*
