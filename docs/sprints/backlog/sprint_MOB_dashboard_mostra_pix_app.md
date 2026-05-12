---
id: MOB-dashboard-mostra-pix-app
titulo: Widget Inbox no dashboard lista pix recebidos do app mobile nas ultimas 24h
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-12
fase: BRIDGE_MOBILE
depende_de: [MOB-bridge-4-inbox-subtipos-reader, MOB-bridge-5-classifier-pix]
esforco_estimado_horas: 3
origem: Plano 2026-05-12 secao Fase B; dono quer ver no dashboard que o pix compartilhado pelo celular chegou e foi classificado.  <!-- noqa: accent -->
mockup: novo-mockup/mockups/16-inbox.html  <!-- noqa: accent -->
---

# Sprint MOB-dashboard-mostra-pix-app -- widget pix vindo do app

## Contexto

A integração app↔backend só fecha quando o dono **vê empíricamente** que o pix que ele compartilhou pelo celular chegou ao dashboard. Sem isso, é fé. Esta sprint adiciona o widget na aba `Inbox` listando arquivos `inbox/financeiro/pix/` enviados pelo app nas últimas 24h, com link para o registro no grafo.

## Objetivo

1. Adicionar bloco "Pix do celular (últimas 24h)" em `src/dashboard/paginas/inbox.py`:
   - Tabela densa: timestamp, valor, recebedor, instituicao_pagadora, status (`processado | pendente | erro`), link para o sidecar `.extracted/<sha8>.json`.
   - Filtro padrão: últimas 24h. Botão "ver últimos 7d / 30d".
   - Sparkline pequeno: quantidade de pix por dia nos últimos 7d.
2. Lógica de leitura:
   - Walk em `<vault>/inbox/financeiro/pix/` onde `<vault>` é configurável via `mappings/sync_config.yaml` ou variável `OUROBOROS_VAULT_PATH` (default `~/Protocolo-Ouroboros/`).
   - **Sidecar canônico do projeto** está em `inbox/.extracted/<sha8>.json` (raiz do repo, **não** no vault Syncthing). Joga a leitura via `Path(__file__).resolve().parents[N] / "inbox" / ".extracted"`.
   - Cruzar com grafo SQLite para descobrir status (`SELECT EXISTS(SELECT 1 FROM node WHERE sha256_arquivo = ?)`).
3. Snapshot atomically (`schema_version=1`) em `~/.ouroboros/cache/pix_recentes.json` para evitar I/O repetido em re-render (refresh manual via botão "atualizar").

## Validação ANTES (grep -- padrão (k))

```bash
grep -n "pix\|Pix" src/dashboard/paginas/inbox.py | head -10
ls ~/Protocolo-Ouroboros/inbox/financeiro/pix/ 2>/dev/null | head
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='documento' AND json_extract(metadata,'\$.tipo_documento')='comprovante_pix_foto'"
.venv/bin/python -c "from src.dashboard.paginas.inbox import render; print('importa OK')"
```

Confirma: (a) inbox.py existe e (b) hoje não cita pix, (c) há pix no grafo após MOB-bridge-5.

## Não-objetivos (padrão (t))

- **NÃO** mover/deletar arquivos do vault.
- **NÃO** processar pix novos a partir do dashboard — o pipeline canônico já cuida (`scripts/processar_inbox_massa.py`).
- **NÃO** mascarar valor de pix (não é PII; CPF/CNPJ sim).
- **NÃO** mostrar pix processados há mais de 30d (escopo da widget é "recentes"; histórico completo fica na aba Extrato).
- **NÃO** depender de DOC-27 ou MOB-bridge-5 implementados para a UI carregar — quando vazio, exibir empty-state.

## Spec de implementação

### Lógica

```python
# src/dashboard/widgets/pix_recentes.py (novo módulo)
import os
from datetime import datetime, timedelta
from pathlib import Path
import json
import sqlite3

from src.intake import sha8_arquivo

_RAIZ_REPO = Path(__file__).resolve().parents[3]
_SIDECAR_DIR = _RAIZ_REPO / "inbox" / ".extracted"     # path real do projeto


def _vault_default() -> Path:
    return Path(os.environ.get("OUROBOROS_VAULT_PATH", "~/Protocolo-Ouroboros")).expanduser()


def listar_pix_recentes(vault_path: Path | None = None, janela_horas: int = 24) -> list[dict]:
    vault = vault_path or _vault_default()
    pix_dir = vault / "inbox" / "financeiro" / "pix"
    if not pix_dir.exists():
        return []
    cutoff = datetime.now() - timedelta(hours=janela_horas)
    items = []
    for arquivo in pix_dir.glob("*"):
        if not arquivo.is_file() or arquivo.suffix.lower() == ".md":
            continue
        stat = arquivo.stat()
        if datetime.fromtimestamp(stat.st_mtime) < cutoff:
            continue
        sha8 = sha8_arquivo(arquivo)
        sidecar = _SIDECAR_DIR / f"{sha8}.json"
        metadata = json.loads(sidecar.read_text()) if sidecar.exists() else {}
        items.append({
            "arquivo": arquivo.name,
            "timestamp": stat.st_mtime,
            "valor": metadata.get("valor"),
            "recebedor": (metadata.get("recebedor") or {}).get("nome"),
            "status": "processado" if metadata.get("tipo_arquivo") == "comprovante_pix_foto" else "pendente",
        })
    return sorted(items, key=lambda x: x["timestamp"], reverse=True)
```

### UI (Streamlit)

```python
# src/dashboard/paginas/inbox.py (edit incremental, padrão (a))
import streamlit as st
from src.dashboard.widgets.pix_recentes import listar_pix_recentes
from src.dashboard.ui import seccao_titulo_html

def render():
    ...   # existing code

    # Bloco novo no topo da pagina
    st.markdown(seccao_titulo_html("Pix do celular (últimas 24h)"), unsafe_allow_html=True)
    pix = listar_pix_recentes(VAULT_PATH, janela_horas=24)
    if not pix:
        st.info("Nenhum pix compartilhado pelo app mobile nas últimas 24h.")
    else:
        st.dataframe(pd.DataFrame(pix), use_container_width=True)
```

### Cache atomico

```python
# src/mobile_cache/pix_recentes.py
def gerar_cache_pix_recentes(vault_path: Path, destino: Path):
    payload = {
        "schema_version": 1,
        "gerado_em": datetime.now().isoformat(),
        "items": listar_pix_recentes(vault_path, janela_horas=24 * 7),  # 7d
    }
    write_json_atomic(destino, payload)
```

## Proof-of-work (padrão (u))

```bash
# 1. Popular vault sintetico
mkdir -p /tmp/vault_pix_teste/inbox/financeiro/pix
mkdir -p /tmp/vault_pix_teste/.extracted
echo '{"sha8":"abc","tipo_arquivo":"comprovante_pix_foto","valor":150.0,"recebedor":{"nome":"FULANO"}}' > /tmp/vault_pix_teste/.extracted/abc12345.json
touch /tmp/vault_pix_teste/inbox/financeiro/pix/2026-05-12-153014-pix.jpg

# 2. Listar
.venv/bin/python -c "
from src.dashboard.widgets.pix_recentes import listar_pix_recentes
from pathlib import Path
print(listar_pix_recentes(Path('/tmp/vault_pix_teste')))
"

# 3. Rodar dashboard (manual, validacao visual)
./run.sh --dashboard
# Acessar pagina Inbox, conferir bloco no topo

# 4. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/ -k "pix or inbox" -q
```

## Critério de aceitação (gate (z))

1. `src/dashboard/widgets/pix_recentes.py` exporta `listar_pix_recentes`.
2. Bloco renderiza em `inbox.py` (validação visual via screenshot side-by-side com mockup `16-inbox.html`).
3. Quando vazio: empty-state amigável (sem erro).
4. Quando popular: tabela densa + sparkline.
5. `tests/test_pix_recentes.py` ≥ 5 testes.
6. Pytest baseline cresce ≥ +5.
7. Gauntlet verde + validação visual aprovada.

## Referência

- Auditoria C1 (app): `docs/auditorias/AUDITORIA_APP_MOBILE_2026-05-12.md`.
- Mockup: `novo-mockup/mockups/16-inbox.html`.
- Sprints dependentes: MOB-bridge-4, MOB-bridge-5.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B.

*"Quando o dono ve no dashboard o que mandou pelo celular, a integracao deixou de ser promessa." — princípio MOB-dashboard-mostra-pix-app*
