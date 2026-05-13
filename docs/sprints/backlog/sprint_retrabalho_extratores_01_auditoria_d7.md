---
id: RETRABALHO-EXTRATORES-01-AUDITORIA-D7
titulo: Sprint RETRABALHO-EXTRATORES-01 -- Auditoria de cada extrator sob D7 + ramificação
  por tipo
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint RETRABALHO-EXTRATORES-01 -- Auditoria de cada extrator sob D7 + ramificação por tipo

**Origem**: pedido do dono em 2026-04-29: "Temos que fazer um trabalho de retrabalho de verdade. De arrumar na origem cada tipo de cada arquivo".
**Prioridade**: P1 (bloqueia confiabilidade da Onda 4 e do IRPF; sem cobertura total na origem, qualquer feature downstream amplifica falha)
**Onda**: independente (cross-cutting, alimenta Ondas 3 + 4 + 6)
**Esforço estimado**: 6h (auditoria + ramificação) + N × 2h-5h (sprints-filhas por extrator com falha de cobertura)
**Depende de**: META-COBERTURA-TOTAL-01 (lint + contrato runtime) **E** VALIDAÇÃO-CSV-01 (ferramenta de marcação humana, arquivo `sprint_validacao_csv_01_tracking_por_arquivo.md`)
**Fecha itens da auditoria**: torna D7 verificável extrator-a-extrator, fechando vício do plan mestre que enumera achados sem auditar 1-a-1

## Problema

Hoje há 20 extratores em `src/extractors/` (excluindo `base.py` e `_ocr_comum.py`). Auditoria honesta nunca foi feita extrator-por-extrator sob a lente de D7 ("extrair tudo, catalogar tudo"). Sabe-se de violações pontuais (DANFE retorna `[]`, OCR energia 67% kWh, holerite sem `codigo_produto` perde verbas), mas o universo completo de campos não-extraídos por extrator nunca foi mapeado.

Pedido do dono: **retrabalho na origem**, extrator por extrator, com validação CSV (Sprint VALIDACAO-CSV-01) e gate de cobertura mínima (Sprint META-COBERTURA-TOTAL-01).

## Hipótese

Auditoria sistemática em 3 etapas resolve:

1. **Etapa 1 -- inventário**: para cada um dos 20 extratores, rodar amostra real, gerar linha no CSV de validação (Sprint VALIDACAO-CSV-01), comparar campos extraídos vs campos potenciais (lidos via Read multimodal pelo Opus interativo).
2. **Etapa 2 -- triagem**: classificar cada extrator em 4 tiers:
   - **Tier A -- cobertura total verificada** (≥95% campos potenciais extraídos, validação humana OK em ≥3 amostras).
   - **Tier B -- gap conhecido pequeno** (cobertura 80-95%; sprint-filha de polish).
   - **Tier C -- gap relevante** (cobertura 50-80%; sprint-filha de retrabalho substantivo).
   - **Tier D -- violação grave** (cobertura <50% OU `extrair() -> []` silencioso; sprint-filha de reescrita).
3. **Etapa 3 -- ramificação**: para cada extrator Tier B/C/D, abrir spec-filha `sprint_retrabalho_<extrator>.md` com escopo + acceptance específicos. Tier A move para registro consolidado em `docs/extractors/cobertura_d7.md`.

## Lista canônica dos 20 extratores a auditar

| # | Extrator | Tipo de origem | Status hoje (hipótese) |
|---|---|---|---|
| 1 | `boleto_pdf` | PDF | Tier B/C provável (linking parcial) |
| 2 | `c6_cartao` | XLS encriptado | Tier A provável (smoke 100%) |
| 3 | `c6_cc` | XLS encriptado | Tier A provável |
| 4 | `contracheque_pdf` | PDF | Tier C (DOC-19 confirma sem `codigo_produto`) |
| 5 | `cupom_garantia_estendida_pdf` | PDF | Tier B/C provável |
| 6 | `cupom_termico_foto` | JPEG | Tier B/C (Sprint 87d ANTI-MIGUE-05 fixou hash, mas cobertura?) |
| 7 | `danfe_pdf` | PDF | **Tier D conhecido** (item 21 do plan: `extrair() -> []` silencioso) |
| 8 | `das_parcsn_pdf` | PDF | Tier A/B (Sprint 107 ok) |
| 9 | `dirpf_dec` | DEC | Tier ? -- nunca auditado |
| 10 | `energia_ocr` | OCR de foto | **Tier C conhecido** (67% precisão kWh) |
| 11 | `garantia` | PDF | Tier ? |
| 12 | `itau_pdf` | PDF | Tier A provável (centavo-a-centavo) |
| 13 | `nfce_pdf` | PDF | Tier A/B (33 arestas contem_item geradas) |
| 14 | `nubank_cartao` | CSV | Tier A provável |
| 15 | `nubank_cc` | CSV | Tier A provável (formato dedicado pós-Armadilha #3) |
| 16 | `ofx_parser` | OFX | Tier B (Sprint Fa em backlog: duplicação accounts) |
| 17 | `receita_medica` | PDF/foto | Tier ? |
| 18 | `recibo_nao_fiscal` | foto | Tier ? |
| 19 | `santander_pdf` | PDF | Tier ? |
| 20 | `xml_nfe` | XML | Tier B/C (DOC-19 dependência -- itens granulares) |

Hipótese é ponto de partida para o Opus que executar. Auditoria real fixa o tier.

## Como começar (operacional para o Opus que assumir esta sprint)

```bash
# Pré-condição: META-COBERTURA-TOTAL-01 e VALIDACAO-CSV-01 fechadas.
# Confira:
ls docs/sprints/concluidos/ | grep -E "meta_cobertura_total|validacao_csv"

# Passo 1 -- Para cada extrator, identificar 3 amostras reais
ls data/raw/_classificar/ data/raw/andre/ data/raw/casal/ data/raw/vitoria/ 2>/dev/null

# Passo 2 -- Rodar pipeline em modo dry-run e capturar baseline do CSV
./run.sh --tudo --dry-run
head -50 data/output/validacao_arquivos.csv

# Passo 3 -- Para cada extrator, abrir 1 amostra via Read multimodal e
#            preencher coluna valor_opus + status_opus no CSV
python scripts/validar_arquivo.py --sha8 <sha8_amostra> --executar
```

## Implementação proposta

### Etapa 1 -- inventário (3h)

1. Rodar pipeline em ambiente isolado (worktree).
2. Para cada um dos 20 extratores, garantir ≥3 amostras representativas no `validacao_arquivos.csv`.
3. Para cada amostra, executar `validar_arquivo.py --sha8 X` -- preenche coluna `valor_opus`.
4. Anotar campos potenciais não detectados pelo extrator (campo presente no doc + lido pelo Opus + ausente no CSV ETL).

### Etapa 2 -- triagem (1h)

5. Gerar relatório `docs/auditorias/extratores_d7_2026-MM-DD.md` com tier de cada extrator + lista de campos faltantes.

### Etapa 3 -- ramificação (2h + N spawns)

6. Para cada extrator Tier B/C/D, criar `sprint_retrabalho_<extrator>.md` em backlog/ com:
   - Hipótese específica do que falta.
   - Lista de campos a passar a extrair.
   - Amostras canônicas referenciadas (sha8).
   - Acceptance: `make conformance-<tipo>` exit 0 com cobertura ≥95% no CSV.
7. Para cada extrator Tier A, registrar em `docs/extractors/cobertura_d7.md` com link para amostras + data da última validação.

## Proof-of-work (runtime real)

- 20 extratores × ≥3 amostras = ≥60 entradas no `validacao_arquivos.csv` com `valor_etl` + `valor_opus` preenchidos.
- Relatório `docs/auditorias/extratores_d7_<data>.md` publicado com tier de cada extrator.
- N sprints-filhas criadas em backlog (estimativa: 8-12 dependendo da taxa real de Tier A).
- Registro consolidado em `docs/extractors/cobertura_d7.md` para Tier A.

## Acceptance criteria

- `validacao_arquivos.csv` tem cobertura mínima de 60 linhas (20 extratores × 3 amostras).
- 100% extratores categorizados em A/B/C/D com evidência.
- Relatório de auditoria publicado.
- Sprint-filha existe para cada extrator Tier B/C/D.
- Tier A consolidado em `docs/extractors/cobertura_d7.md`.
- Lint META-COBERTURA-TOTAL-01 verde após esta sprint (pode falhar antes -- esperado).

## Como saber que terminou

1. Relatório auditoria publicado.
2. ≥1 sprint-filha por extrator com tier ≠ A.
3. `docs/extractors/cobertura_d7.md` listando Tier A explicitamente.
4. `git log --grep="retrabalho_"` retorna ≥8 commits novos (uma por sprint-filha criada).
5. Frontmatter `concluida_em: <data>` adicionado a esta spec.
6. Esta spec move para `concluidos/`. Sprints-filhas continuam em backlog até cada uma fechar individualmente.

## Achados colaterais durante execução

- Se descobrir que dois extratores compartilham bug similar (ex: ambos amostram primeiras 5 linhas) → criar `sprint_refactor_<area>_compartilhada.md`.
- Se descobrir que falta extrator para tipo encontrado em amostra → invocar skill `/propor-extrator <tipo>` e criar spec via fluxo padrão.
- Se descobrir PII vazando em CSV de validação → criar sprint urgente de redactor (P0).
- Se uma amostra for ambígua (mesmo Opus + humano discordam do que é "extraível") → registrar em `docs/auditorias/ambiguidades_d7.md` para discussão futura.

## Gate anti-migué

1. Hipótese validada com grep + ls antes de codar (Passos 1-3 de "Como começar").
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` ainda não se aplica nesta sprint (aplica nas filhas).
4. `make lint` exit 0.
5. `make smoke` 10/10.
6. `pytest` baseline mantida.
7. **Cada extrator Tier B/C/D deve virar sprint-filha. Zero TODO solto, zero "auditar depois", zero "ver caso a caso".**
8. Validador APROVOU.
9. Frontmatter `concluida_em`.

## Referências

- Pedido literal do dono em 2026-04-29.
- META-COBERTURA-TOTAL-01 (sprint irmã, lint + contrato).
- VALIDAÇÃO-CSV-01 (sprint irmã, ferramenta CSV; arquivo `sprint_validacao_csv_01_tracking_por_arquivo.md`).
- Decisão D7 em `~/.claude/plans/glittery-munching-russell.md`.
- ANTI-MIGUE-01 (gate 4-way) -- aplicado a cada sprint-filha.
- Item 21 do plan `pure-swinging-mitten` (DANFE silencia falha) -- exemplo Tier D.
- Item 23 (OCR energia 67%) -- exemplo Tier C.
- DOC-19 (holerite contem_item sem código) -- exemplo Tier C, já em backlog.
