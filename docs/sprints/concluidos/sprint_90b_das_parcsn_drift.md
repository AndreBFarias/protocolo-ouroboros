---
concluida_em: 2026-04-26
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 90b
  title: "DAS PARCSN drift -47%: investigar 9 PDFs unicos sem node no grafo"
  prioridade: P0
  estimativa: 2-3h
  origem: "auditoria 2026-04-26 ETL -- 19 PDFs unicos vs 10 nodes (drift -47%)"
  touches:
    - path: src/extractors/das_parcsn_pdf.py
      reason: "investigar parser; possivel falha em PDFs scaneados ou formato variante"
    - path: src/extractors/boleto_pdf.py
      reason: "verificar se boleto_pdf esta capturando arquivos parcsn antes (ordem em pipeline.py)"
    - path: tests/test_das_parcsn_drift.py
      reason: "fixture sintetica + 9 hashes especificos como amostras"
  forbidden:
    - "Mexer no contrato do grafo (nodes/edges) sem ADR-14-update"
    - "Aceitar fix sem rodar runtime real e validar 19/19 nodes"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_das_parcsn_drift.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Apos fix, 19 PDFs unicos -> 19 nodes no grafo (delta 0)"
    - "Os 9 PDFs faltantes (lista no apendice B) são processados sem erro"
    - "Idempotencia preservada: re-rodar não duplica nodes"
    - "Teste regressivo cobre cada uma das 4 variacoes possiveis (PDF nativo, PDF scaneado, formato com/sem QRCode SENDA)"
  proof_of_work_esperado: |
    # Antes
    sqlite3 data/output/grafo.sqlite \
      "SELECT COUNT(*) FROM node WHERE tipo='documento' AND json_extract(metadata, '\$.tipo_documento')='das_parcsn_andre';"
    # = 10
    
    find data/raw/andre/impostos/das_parcsn -type f -name '*.pdf' | xargs -I{} sha256sum {} | awk '{print $1}' | sort -u | wc -l
    # = 19
    
    # Investigar 1 dos faltantes
    .venv/bin/python -c "
    from src.extractors.das_parcsn_pdf import ExtratorDASPARCSNPDF
    from pathlib import Path
    p = Path('data/raw/andre/impostos/das_parcsn/<hash_faltante>.pdf')
    e = ExtratorDASPARCSNPDF(p)
    print(f'pode_processar: {e.pode_processar(p)}')
    res = e.extrair()
    print(f'resultado: {res}')
    "
    
    # Depois (apos fix)
    ./run.sh --tudo
    sqlite3 data/output/grafo.sqlite \
      "SELECT COUNT(*) FROM node WHERE tipo='documento' AND json_extract(metadata, '\$.tipo_documento')='das_parcsn_andre';"
    # = 19
```

---

# Sprint 90b -- DAS PARCSN drift -47%

**Status:** BACKLOG (P0, criada 2026-04-26)
**Origem:** agente ETL contou 19 SHAs unicos em `data/raw/andre/impostos/das_parcsn/` mas grafo tem 10 nodes do tipo. Gap -47%.

## 9 PDFs faltantes confirmados

Lista do apendice B do relatório:

1. `2025-02-28_a135a39f`
2. `2025-03-31_9a445c44`
3. `2025-03-31_b3f11503`
4. `2025-04-30_ab9ae6e3`
5. `2025-05-30_29d42c07`
6. `2025-07-31_996ccc3f`
7. `2025-10-31_96469f32`
8. `2025-12-30_ba1faf52`
9. `2026-03-31_c2bdf7e2`

São 9 parcelas espalhadas (fev a dez/2025 + mar/2026). Não parece ser problema de mes especifico.

## Investigacao dirigida

Suspeitas a confirmar **antes** de tocar código:

1. **Boleto PDF roubando antes**: `pipeline.py::_descobrir_extratores` tem `das_parcsn_pdf` em linha 153-156 e `boleto_pdf` em linha 168-176. Boleto vem DEPOIS, entao não rouba. Hipotese descartada.

2. **PDF scaneado com OCR-fallback não implementado no das_parcsn_pdf**. Sprint 89 implementou OCR fallback so em `intake/preview.py` e `nfce_pdf.py`. Se os 9 PDFs faltantes são imagens scaneadas, das_parcsn_pdf retorna texto vazio e não parseia. **Provavel.**

3. **Formato variante** (PDF emitido por sistema diferente da Receita Federal). Investigar se cabecalho difere.

4. **Hash duplicado mas conteúdo diferente** (improvavel pois agente confirmou 19 SHAs distintos).

## Escopo

### Fase 1 -- Diagnosticar (1h)

Para cada um dos 9 PDFs faltantes:

```bash
.venv/bin/python << 'EOF'
import pdfplumber
from pathlib import Path
faltantes = ['a135a39f', '9a445c44', 'b3f11503', 'ab9ae6e3', '29d42c07', 
             '996ccc3f', '96469f32', 'ba1faf52', 'c2bdf7e2']
pasta = Path('data/raw/andre/impostos/das_parcsn')
for sha in faltantes:
    pdfs = list(pasta.glob(f'*{sha}*.pdf'))
    if not pdfs:
        print(f'{sha}: NAO ENCONTRADO em raw/')
        continue
    pdf = pdfs[0]
    with pdfplumber.open(pdf) as doc:
        chars_pag1 = len(doc.pages[0].extract_text() or '')
        print(f'{sha}: {chars_pag1} chars pag1')
EOF
```

Se `chars_pag1 < 50` para varios -> hipotese 2 confirmada (PDF scaneado).

### Fase 2 -- Fix dirigido

Adicionar OCR fallback em `das_parcsn_pdf.py` (mesmo padrao da Sprint 89/A2). Importar `pypdfium2 + pytesseract`, fallback se `pdfplumber.extract_text()` retornar `< 50` chars.

### Fase 3 -- Validação em volume real

Rodar `./run.sh --tudo`. Confirmar 19/19 nodes no grafo.

### Fase 4 -- Teste regressivo

`tests/test_das_parcsn_drift.py`:
- Fixture sintetica: PDF nativo com "DAS PARCSN" + valor + nº SENDA -> 1 node.
- Fixture sintetica: PDF imagem (renderizado a partir de texto, scale=2 simulando scan) -> 1 node via OCR fallback.

## Armadilhas

- **OCR via tesseract pode confundir digitos**. Número SENDA tem que bater exato como chave do grafo. Validar com regex pos-OCR.
- **Performance**: OCR em 9 PDFs adiciona ~30s ao pipeline. Aceitavel.

## Dependencias

- Nenhuma. Pode rodar antes ou depois das outras Sprints P0.

---

*"Drift de 47% não eh ruido, eh sinal." -- principio da auditoria que cobra explicacao*
