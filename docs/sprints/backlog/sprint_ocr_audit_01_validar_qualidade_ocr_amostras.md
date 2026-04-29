# Sprint OCR-AUDIT-01 -- Auditoria de qualidade de OCR (5 amostras por extrator com OCR)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 3
**Esforço estimado**: 5h
**Depende de**: ANTI-MIGUE-01
**Fecha itens da auditoria**: achado da auditoria de banco 2026-04-29

## Problema

Extratores que dependem de OCR (energia_ocr, contracheque_pdf fallback Infobase, cupom_termico_foto, nfce com OCR de imagem) podem extrair valores errados sem o pipeline detectar. ARMADILHA #10 do CLAUDE.md confirma: energia_ocr tem 67% precisão em consumo kWh. Outros extratores OCR podem ter problemas similares não-medidos.

## Hipótese

Amostrar 5 documentos por extrator OCR. Para cada amostra, comparar: (a) texto OCR bruto vs (b) campos extraídos pelo pipeline vs (c) verdade ground-truth marcada por humano via Revisor 4-way. Computar precisão por campo.

## Implementação proposta

1. tests/ocr_audit/ com fixtures reais (5 PDFs/fotos por extrator OCR, total ~25).
2. scripts/auditar_ocr.py que roda extrator e compara com ground-truth em YAML.
3. Relatório data/output/auditoria_ocr.md com precisão por campo por extrator.
4. Para campos com precisão <90%, criar sprint-filha de fix.

## Proof-of-work (runtime real)

Relatório com >=25 amostras, precisão por campo, lista de campos abaixo de 90% com sprint-filha apontada.

## Acceptance criteria

- Fixtures + ground-truth.
- Script + relatório.
- Sprints-filhas para gaps detectados.
- Baseline de qualidade documentado.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` exit 0 quando aplicável (>=3 amostras 4-way).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
