## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 89
  title: "OCR pré-classificação para PDFs-imagem sem texto extraível"
  touches:
    - path: src/intake/preview.py
      reason: "detectar PDF com 0 chars extraíveis e invocar tesseract como fallback pré-classifier"
    - path: mappings/tipos_documento.yaml
      reason: "regras existentes (cupom_fiscal_foto, garantia_fabricante, nfce_consumidor_eletronica) passam a casar previews gerados por OCR"
    - path: tests/test_intake_preview_ocr.py
      reason: "novo: fixture PDF-imagem sintético + asserção de preview não-vazio"
  forbidden:
    - "Alterar regras de tipos_documento.yaml (Sprint 88 calibrou)"
    - "OCR em PDFs que já retornam texto nativamente (performance -- só fallback)"
    - "Substituir extrator de cupom_termico_foto (que faz OCR full-quality com deskew); este é só preview"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "./run.sh --inbox-dry"
  acceptance_criteria:
    - "PDF-imagem sem texto extraível gera preview via tesseract (>=200 chars) quando pdfplumber retorna vazio"
    - "'notas de garantia e compras.pdf' do inbox/ passa a detectar em um dos tipos fiscais (NFCe, DANFE, cupom_foto, ou garantia)"
    - "PDFs com texto nativo continuam sem OCR (performance preservada)"
    - "Timeout de OCR em 30s por página; falha gera preview vazio + log warning (pipeline não trava)"
    - "./run.sh --inbox-dry >=26/27 arquivos roteados (hoje 26/27; spec fecha o último)"
    - "Zero regressão: baseline 1137 passed / 10 skipped (pós-Sprint 88) preservado"
  proof_of_work_esperado: |
    # Antes da Sprint 89
    .venv/bin/python -c "
    import pdfplumber
    with pdfplumber.open('inbox/notas de garantia e compras.pdf') as pdf:
        for p in pdf.pages: print(len(p.extract_text() or ''))
    "
    # Esperado: 0 0 0 0 (4 páginas sem texto)

    # Depois
    ./run.sh --inbox-dry 2>&1 | grep -c 'skip_nao_identificado'  # <= 1
    # "notas de garantia e compras.pdf" deve aparecer com tipo casado
```

---

# Sprint 89 — OCR pré-classificação para PDFs-imagem

**Status:** BACKLOG
**Prioridade:** P3 (não-bloqueante; 96% da ingestão funciona; cobre o 4% residual)
**Dependências:** Sprint 88 (regras YAML calibradas), tesseract-ocr já instalado (install.sh §33)
**Origem:** achado colateral Sprint 88 em 2026-04-24

## Problema

`./run.sh --inbox-dry` da Sprint 88 deixou 1 arquivo em `skip_nao_identificado`: `notas de garantia e compras.pdf` (4 páginas). Inspeção mostra que pdfplumber retorna **0 chars em todas as páginas** — é PDF composto por imagens puras (provavelmente scan ou screenshot de notas fiscais / termos de garantia).

O `src.intake.preview` extrai texto via pdfplumber para o classifier avaliar regex. PDF-imagem rompe o fluxo: sem texto, nenhuma regra casa, `skip_nao_identificado` silencioso.

## Solução

Fallback OCR pré-classificação:

1. `preview.py` tenta pdfplumber primeiro (rápido, zero custo).
2. Se resultado é **vazio** (ou < N chars, ex.: 50) E MIME é `application/pdf`:
   a. Render primeira página como imagem PIL via `pypdfium2` (já é dep do projeto).
   b. `pytesseract.image_to_string(img, lang='por', timeout=30)`.
   c. Se OCR retorna >= 200 chars, usa como preview.
   d. Se falha ou chars < 200, devolve vazio (classifier cai em skip motivado, mas agora com razão "ocr_vazio").
3. Classifier roda regex como de costume — regras existentes (NFCe, DANFE, cupom_foto, garantia_fabricante) casam texto OCR normalmente.

## Escopo

### 89.1 — Detectar PDF-imagem em preview.py

Heurística em `src.intake.preview`:

```python
def _extrair_texto_pdf_ou_ocr(caminho: Path) -> str:
    with pdfplumber.open(caminho) as pdf:
        texto = "\n".join(p.extract_text() or "" for p in pdf.pages[:3])
    if len(texto.strip()) >= 50:
        return texto  # rota normal; sem custo de OCR
    return _preview_via_ocr(caminho, paginas=1, timeout_s=30)
```

### 89.2 — Helper `_preview_via_ocr`

```python
def _preview_via_ocr(caminho: Path, paginas: int = 1, timeout_s: int = 30) -> str:
    try:
        import pypdfium2
        import pytesseract
    except ImportError:
        logger.warning("pypdfium2/pytesseract indisponível; preview OCR pulado")
        return ""
    try:
        pdf = pypdfium2.PdfDocument(caminho)
        texto_total: list[str] = []
        for i in range(min(paginas, len(pdf))):
            pil_img = pdf[i].render(scale=2).to_pil()
            texto = pytesseract.image_to_string(
                pil_img, lang="por", timeout=timeout_s
            )
            texto_total.append(texto)
        return "\n".join(texto_total)
    except Exception as exc:
        logger.warning("OCR preview falhou em %s: %s", caminho.name, exc)
        return ""
```

### 89.3 — Teste

`tests/test_intake_preview_ocr.py`:
- Fixture PDF-imagem sintético (pode usar pdfkit/reportlab para gerar PDF com imagem embutida, ou mockar pdfplumber+pypdfium2).
- Asserção: preview retorna string não-vazia quando pdf tem imagens + texto OCRizável.
- Regressão: preview para PDF nativo (com texto) não invoca OCR (via mock de pypdfium2).

### 89.4 — Performance

Timeout agressivo (30s) + 1 página apenas (preview, não extração full). PDF-imagem verdadeiro fica em OCR; PDF nativo não paga nada.

## Armadilhas

- `pypdfium2` pode estar como dep transitiva; verificar via `pip show pypdfium2` antes de assumir import.
- Qualidade do OCR no preview é inferior ao extrator dedicado (cupom_termico_foto faz deskew + thresholding). Isso é OK — preview só precisa de âncora regex casável, não de recall exato.
- PDFs com texto + imagem (mistos) retornam texto nativo; OCR não é chamado. Comportamento correto.

---

*"Onde o texto cala, a imagem fala -- se souber escutar." -- princípio do OCR fallback*
