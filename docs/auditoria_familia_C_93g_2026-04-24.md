# Auditoria família C (Sprint 93g) — limpeza de clones mal-roteados

**Data:** 2026-04-24
**Sprint:** 93g
**Sprint-pai:** 93f (rotulagem canônica Nubank PF/PJ + hash anti-colisão)

## Contexto

Sprint 93f resolveu duas dimensões do bug PJ (normalizer + hash do cartão), mas validação runtime mostrou que tx `Nubank (PJ)` continuavam em zero no XLSX, apesar dos extratores produzirem 841 tx PJ (275 cartão + 566 CC) em ambiente isolado. Investigação expôs causa operacional: **91 arquivos em diretórios PF eram clones SHA-idênticos dos arquivos PJ canônicos**, colapsando o lado PJ no dedup.

## Diagnóstico

Script de comparação SHA-256 entre `data/raw/vitoria/nubank_pj_{cartao,cc}/` e `data/raw/{andre,vitoria}/nubank_{cartao,cc}/` identificou **91 clones exatos**:

| Diretório clones | Qtd | Origem canônica |
|---|---:|---|
| `data/raw/andre/nubank_cartao/BANCARIO_NUBANK_CARTAO_*.csv` | 84 | `vitoria/nubank_pj_cartao/Nubank_*.csv` (11 originais, cada um com 7-14 cópias) |
| `data/raw/andre/nubank_cc/BANCARIO_NUBANK_CC_*.csv` | 4 | `vitoria/nubank_pj_cc/cc_pj_vitoria.csv` |
| `data/raw/vitoria/nubank_cc/BANCARIO_NUBANK_CC_*.csv` | 3 | `vitoria/nubank_pj_cc/cc_pj_vitoria.csv` |

Causa provável: `inbox_orchestrator` histórico rotulou faturas PJ como PF do André e propagou sufixos `_1.csv`, `_2.csv`, ... em reprocessamentos sucessivos.

## Ação

Deletei os 91 clones. Decisão segura porque:

- SHA-256 idêntico aos canônicos em `data/raw/vitoria/nubank_pj_*/` -- zero perda de conteúdo.
- `.gitignore` exclui `data/` inteiro -- não há versionamento.
- ADR-18 satisfeito pela existência do canônico (é o próprio "original imutável").

## Resultado runtime

`./run.sh --tudo` re-executado após limpeza:

| Métrica | Pré-93f | Pós-93f | Pós-93g |
|---|---:|---:|---:|
| `Nubank (PJ)` no XLSX | 0 | 0 | **828** |
| `Nubank (PF)` → Vitória | 0 | 2310 | 1757 |
| Vitória total tx | 575 | 2885 | **3160** |
| Casal total tx | 2310 | 0 | 0 |

Valor absoluto das 828 tx PJ: **R$ 169.131,13**. Todas com `quem=Vitória` (100%).

A redução em `Nubank (PF)` (2310 → 1757) reflete tx que realmente pertenciam a PJ e foram reclassificadas.

## Gauntlet

- `make lint` OK
- `.venv/bin/pytest tests/ -q`: 1537 passed / 9 skipped / 1 xfailed
- `make smoke`: 23 checagens / 0 erros + 8/8 contratos aritméticos

## Ressalvas

Nenhuma sprint-filha formalizada. A causa raiz (inbox_orchestrator histórico) pode ser endereçada pela Sprint 93d (preservação forte de downloads + reprocessamento cronológico) já no backlog, mas é P2 e não bloqueia visibilidade PJ a partir daqui.

---

*"Um arquivo na pasta errada é um dado fora de lugar; um dado fora de lugar é uma decisão errada esperando para acontecer." -- princípio do roteamento canônico*
