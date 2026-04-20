---
id: 2026-04-20_notas-garantia-scan-nfce
tipo: classificacao  # noqa: accent
data: 2026-04-20
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: 44b
---

# Proposta de classificação: notas de garantia e compras.pdf (scan heterogêneo)

## Arquivo

- **Caminho atual:** `data/raw/_classificar/_CLASSIFICAR_6c1cc203.pdf`
- **Nome original na inbox:** `notas de garantia e compras.pdf`
- **MIME detectado:** `application/pdf` (4 páginas, todas escaneadas -- 0 chars via pdfplumber)
- **Tamanho:** ~5MB
- **Motivo da não-classificação:** classifier da Sprint 41d faz preview via
  `pdfplumber.extract_text()`. Scan puro devolve 0 chars, nenhuma regex de
  `mappings/tipos_documento.yaml` casa, arquivo fica em `_classificar/`.

Conteúdo verificado via OCR manual (`pytesseract`):
- pg 1: NFC-e Americanas (compra 2 itens P55, R$ 629,98 PIX)
- pg 2: Bilhete Garantia Estendida MAPFRE (duplicata do `pdf_notas.pdf`)
- pg 3: Bilhete Garantia Estendida MAPFRE (duplicata)
- pg 4: NFC-e Americanas (supermercado 29 itens, R$ 571,52 PIX)

## Tipo sugerido

PDF **heterogêneo scan**. `mappings/tipos_documento.yaml` já tem os 2 tipos
necessários (`nfce_consumidor_eletronica`, `cupom_garantia_estendida`) --
o gap é na camada de preview.

**Ação imediata (baixo custo, humano):**
1. Humano roda `pdftoppm -r 200 notas.pdf page -png` para extrair imagens
2. `pytesseract` gera .txt por página
3. Re-inserção no intake como .png + .txt para classificador casar

**Ação sistêmica (sprint futura):**
- Abrir Sprint 41e (ou fundir com 45): OCR-preview para scans heterogêneos.
  `src/intake/extractors_envelope.py:expandir_pdf_multipage` deteta 0 chars
  em todas páginas e aplica tesseract antes do classifier.

## Regra nova

Nenhuma regex nova em `tipos_documento.yaml`. O gap é de pipeline de preview,
não de taxonomia. Proposta de Sprint 41e a abrir separadamente.

## Decisão humana

**Aprovada em:** (preencher ao aprovar)
**Ação realizada ao aprovar (marcar uma):**
- [ ] Quebrar manualmente em 4 PDFs (ação imediata)
- [ ] Manter em `_classificar/` + abrir Sprint 41e (ação sistêmica)

**Rejeitada em:** (preencher ao rejeitar)
**Motivo:** (se rejeitada)

---

*"A classificação é o primeiro ato de leitura." -- princípio de arquivista*
