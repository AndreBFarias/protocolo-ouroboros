# Arquitetura de sync vault ↔ desktop

> **Origem**: Sprint UX-V-04 (Onda V — paridade visual). Princípio: o
> dashboard deve falar quando o pipeline de dados rodou.

## Pipeline canônico

```
[App Android Protocolo-Mob-Ouroboros]
        │ writes registros .md (humor, diário, daily/YYYY-MM-DD.md)
        ▼
[Vault Obsidian compartilhado em ~/Documents/Obsidian/Casal/]
        │ git push (manual ou automático)
        ▼
[GitHub privado — repo do vault]
        │ git pull no desktop
        ▼
[Vault Obsidian local (mesmo path)]
        │ src/obsidian/sync_rico.py varre grafo + escreve notas
        │ src/mobile_cache/*.py extrai humor/diário/etc.
        ▼
[.ouroboros/cache/*.json -- humor-heatmap.json, last_sync.json, ...]
        │ leitura cacheada por src/dashboard/
        ▼
[Streamlit dashboard]
```

## Contrato `last_sync.json`

Gravado por `src.obsidian.sync_rico._gravar_last_sync` ao final de toda
execução real (não dry-run) de `sincronizar_rico`. Caminho:

```
<raiz_repo>/.ouroboros/cache/last_sync.json
```

Schema:

```json
{
  "data": "2026-05-07T14:32:18-03:00",
  "n_arquivos": 142,
  "fonte": "vault_obsidian",
  "vault_path": "/home/<user>/Documents/Obsidian/Casal",
  "duracao_segundos": 4.7,
  "erros": []
}
```

Campos:

| Campo | Tipo | Descrição |
|---|---|---|
| `data` | str ISO 8601 com tz | Timestamp do final da sincronização |
| `n_arquivos` | int | Total de notas escritas (docs + fornecedores + MOCs) |
| `fonte` | str | Sempre `"vault_obsidian"` (futuro: `"belvo"`, `"gmail"`) |
| `vault_path` | str | Path absoluto do vault sincronizado |
| `duracao_segundos` | float | Tempo decorrido em segundos (2 casas) |
| `erros` | list[str] | Lista de erros não-fatais (ADR-10 graceful) |

## Indicador visual

Renderizado por `src.dashboard.componentes.ui.sync_indicator_html()`.
Variantes:

| Idade da sync | Classe CSS | Rótulo |
|---|---|---|
| `< 1h` | `.sync-indicator` (verde) | `sync agora (Nmin atrás)` |
| `1h – 24h` | `.sync-indicator.sync-indicator-stale` (amarelo) | `sync Nh atrás` |
| `> 24h` ou nunca | `.sync-indicator.sync-indicator-stale` | `sync Nd atrás (rode --sync)` |

Posicionamento canônico: logo abaixo do `page-header`, em wrapper alinhado
à direita (`.sync-indicator-wrapper`). Páginas-vitrine: Bem-estar /
Hoje, Humor, Diário (UX-V-04). Outras páginas podem optar in-line.

## Como rodar a sync

```bash
./run.sh --sync     # entrada canônica (orquestra sync_rico + caches)
make sync           # alternativa via Makefile
```

## ADRs aplicáveis

- **ADR-10** — Resiliência a Dados Incompletos: gravação e leitura de
  `last_sync.json` capturam exceções e seguem em frente.
- **ADR-15** — Intake universal: vault é mais uma fonte; `fonte` no
  payload abre caminho para Belvo/Gmail no futuro.
- **ADR-18** — Integração com sistema vivo (Controle de Bordo).

## Não-objetivos (escopo fechado da sprint)

- Sync incremental ou agendado (escopo MON-01).
- Polling no dashboard / cache invalidation reativa.
- Escrita no vault a partir do dashboard.

*"O sistema honesto fala quando faz e quando deixou de fazer." — princípio V-04*
