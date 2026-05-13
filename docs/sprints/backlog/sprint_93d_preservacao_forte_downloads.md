---
id: 93D-PRESERVACAO-FORTE-DOWNLOADS
titulo: 0. SPEC (machine-readable)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-24'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: "93d"
  title: "Preservação forte de downloads bancários + reprocessamento cronológico"
  depends_on:
    - sprint_id: 93b
      artifact: "docs/auditoria_familia_B_2026-04-24.md"
  touches:
    - path: src/inbox_processor.py
      reason: "Garantir que TODO download recebido vá para data/raw/originais/<sha256>.ext mesmo quando ha arquivo mais recente substituindo-o no raw"
    - path: scripts/reprocessar_cronologico.py
      reason: "Novo script que merge extratos históricos preservados + atuais antes do pipeline"
    - path: tests/test_preservacao_originais.py
      reason: "Testes de integridade: 100% dos downloads históricos preservados"
    - path: docs/auditoria_familia_B_2026-04-24.md
      reason: "Atualizar com resultados da sprint 93d"
  forbidden:
    - "Apagar arquivos de data/raw/originais/ para liberar espaço (são snapshot imutável)"
    - "Reescrever XLSX consolidado a partir de reprocessamento sem backup do atual"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_preservacao_originais.py -v"
    - cmd: ".venv/bin/python scripts/reprocessar_cronologico.py --dry-run"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Todo arquivo ingerido pelo inbox_processor tem cópia em data/raw/originais/<sha256>.ext"
    - "Testes validam que reingestão do mesmo arquivo é idempotente (não duplica)"
    - "Novo script scripts/reprocessar_cronologico.py reconstrói XLSX a partir de data/raw/originais/ em ordem cronológica"
    - "Auditor nubank_pf_cc reduz delta para <R$ 10k após reprocessamento cronológico com originais preservados a partir de 2026-04"
    - "Documentação atualiza estratégia de preservação em docs/ARCHITECTURE.md"
```

---

# Sprint 93d — Preservação forte de downloads + reprocessamento cronológico

**Status:** BACKLOG
**Prioridade:** P2
**Origem:** `docs/auditoria_familia_B_2026-04-24.md` — caso `nubank_pf_cc`

## Problema

A auditoria da família B (Sprint 93b) detectou que o XLSX consolidado
tem **808 transações do Nubank (PF)** nos meses de out-dez/2024 que
NÃO existem mais nos CSVs brutos atuais de `data/raw/vitoria/nubank_pf_cc/`.
O CSV de nov/2024, por exemplo, hoje tem apenas 1 linha — mas o XLSX
tem 129 tx daquele mês em `banco_origem='Nubank (PF)'`.

Causa raiz: downloads mais recentes do Open Finance (ou manuais via
portal Nubank) substituíram os CSVs antigos com conteúdo parcial/vazio.
O pipeline preservou as tx antigas no XLSX (idempotência por
`_identificador`), mas os **CSVs brutos foram sobrescritos**. Não é
possível hoje reproduzir a extração daquelas 808 tx.

Além disso, `find data/raw/originais -name "NU_*"` retorna 0 arquivos
— a preservação por SHA em `data/raw/originais/` não existia quando
esses downloads foram processados.

## Escopo

### Fase 1 — Preservação forte (inbox_processor)

- Toda vez que `inbox_processor` move um arquivo de `inbox/` para
  `data/raw/<pessoa>/<banco>/`, também gera cópia em
  `data/raw/originais/<sha256>.ext` (se não existe ainda).
- Se o SHA já existe em `originais/`, NÃO sobrescreve (idempotência
  absoluta).
- Log explícito de cada preservação: `[INBOX] preservado originais/<sha>.csv`.
- Teste: reingerir 3x o mesmo arquivo gera exatamente 1 cópia em
  `originais/`.

### Fase 2 — Reprocessamento cronológico

- Novo script `scripts/reprocessar_cronologico.py`:
  1. Lista arquivos em `data/raw/originais/` agrupados por banco (via
     detecção de conteúdo, não nome).
  2. Para cada banco, ordena arquivos por data-mínima-das-tx extraídas
     (não mtime do arquivo).
  3. Alimenta o pipeline em ordem, permitindo que versões mais antigas
     preservem tx que versões mais novas removeram.
  4. Dedup nível 1/2 do pipeline converge naturalmente.
- Modo `--dry-run` default, `--executar` explícito.

### Fase 3 — Validação no auditor

- `auditar_extratores.py --banco nubank_pf_cc --modo-abrangente` após
  Sprint 93d deve reduzir delta para <R$ 10k (meta indicativa, ajustar
  conforme dados disponíveis).
- Se o delta residual ainda for grande, documentar como dataloss
  *pré-2026-04* (anterior ao início da preservação forte).

## Armadilhas

- **Performance:** preservar downloads grandes (OFX de 4 anos = 312 KB
  cada, 100 extratos = 30 MB) pode crescer `data/raw/originais/` sem
  controle. Estratégia: cópia é idempotente por SHA, então duplicatas
  (cópias `_1.pdf`, `_2.pdf`) NÃO somam.
- **Detecção de banco por conteúdo:** `data/raw/originais/<sha>.ext`
  não carrega hint de banco no nome. Reusar `file_detector.py` para
  detectar a partir do conteúdo.
- **Colisão de datas:** se o mesmo mês tem 3 downloads históricos com
  conteúdos divergentes (bug do export Nubank), a dedup do pipeline
  pode convergir em caminho errado. Testar empiricamente antes de
  declarar sprint concluída.

## Validação

```bash
# Antes (com arquivos atuais):
.venv/bin/python scripts/auditar_extratores.py \
    --banco nubank_pf_cc --modo-abrangente --deduplicado
# Delta atual: R$ 268.891,17

# Depois da Sprint 93d:
.venv/bin/python scripts/reprocessar_cronologico.py --executar
.venv/bin/python scripts/auditar_extratores.py \
    --banco nubank_pf_cc --modo-abrangente --deduplicado
# Meta: delta < R$ 10.000 (se todos originais preservados)
# OU: delta residual documentado como dataloss pré-2026-04
```

---

*"O que não é preservado é perdido; o que não é reprocessado é
esquecido." — princípio de memória institucional*
