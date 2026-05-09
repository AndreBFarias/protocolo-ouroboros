---
id: INFRA-OCR-OPUS-VISAO
titulo: Opus multimodal como OCR canônico de imagens (cupom_foto, comprovante_foto, recibo)
status: concluída
concluida_em: 2026-05-08
commit: d7f8805
prioridade: altissima
data_criacao: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: []
co_executavel_com: [INFRA-PROCESSAR-INBOX-MASSA]
esforco_estimado_horas: 6
origem: docs/auditorias/VALIDACAO_END2END_2026-05-08.md (caso 2 — cupom JPEG 0/5 processados; OCR atual erra "P55" vs "PS5")
mockup: novo-mockup/mockups/16-inbox.html
---

# Sprint INFRA-OCR-OPUS-VISAO — Opus como OCR canônico para imagens

## Contexto

Validação fim-a-fim em 2026-05-08 mostrou que (a) OCR local erra texto óbvio (gravou "CONTROLE P55" em vez de "PS5" — PlayStation 5), e (b) cupons fotografados (JPEG) têm 0/5 cobertura por OCR atual. Em paralelo, Opus multimodal (este modelo, embutido no fluxo do supervisor artesanal ADR-13) leu cupom Comercial NSP de 52 itens, R$ 513,31, sem erros perceptíveis.

Esta sprint promove Opus a OCR canônico de imagens, com fallback para OCR local quando offline.

## Objetivo

1. Criar `src/extractors/opus_visao.py` com função `extrair_via_opus(caminho_imagem) -> dict`.
   - Em modo supervisor artesanal: emite prompt `Read /caminho/imagem` para o Claude Code. Cache por sha256 em `data/output/opus_ocr_cache/<sha256>.json`.
   - Em modo produção (futuro): chama Anthropic API com `messages.create(model="claude-opus-4-7", content=[{"type":"image","source":...}])`. Cache idem.
2. Schema de saída canônico:
   ```json
   {
     "sha256": "...",
     "tipo_documento": "cupom_fiscal_foto|comprovante_pix_foto|recibo_foto|outro",
     "estabelecimento": {"razao_social": "...", "cnpj": "...", "endereco": "..."},
     "data_emissao": "YYYY-MM-DD",
     "horario": "HH:MM:SS",
     "operador": "string|null",
     "itens": [{"codigo": "...", "descricao": "...", "qtd": float, "unidade": "...", "valor_unit": float, "valor_total": float}],
     "total": float,
     "forma_pagamento": "dinheiro|debito|credito|pix|...",
     "extraido_via": "opus_v4_7|ocr_local",
     "confianca_global": float,
     "ts_extraido": "ISO"
   }
   ```
3. Atualizar `src/intake/inbox_reader.py:processar_fila()` para rotear JPEG/PNG via `opus_visao.extrair_via_opus`.
4. Validador: `mappings/schema_opus_ocr.json` (JSON Schema) + 3 amostras reais em `tests/fixtures/opus_ocr/`.

## Validação ANTES (grep — padrão `(k)`)

```bash
ls src/extractors/ | grep -i ocr
grep -rn "PaddleOCR\|tesseract\|pytesseract" src/ | head
ls data/output/opus_ocr_cache/ 2>&1 | head
```

## Não-objetivos

- NÃO eliminar OCR local — fica como fallback offline.
- NÃO chamar Anthropic API automaticamente nesta sprint (modo supervisor artesanal preserva ADR-13).
- NÃO mexer em extratores estruturados de PDF (NFCe/holerite) que já funcionam.

## Spec de implementação (modo supervisor artesanal)

### `src/extractors/opus_visao.py`

```python
def extrair_via_opus(caminho: Path) -> dict:
    """Lê imagem via Opus multimodal e retorna schema canônico.

    Modo supervisor artesanal (ADR-13): a função NÃO chama API.
    Em vez disso, emite log estruturado pedindo ao supervisor humano
    que invoque ``Read <caminho>`` no Claude Code e cole o resultado
    em ``data/output/opus_ocr_pendentes/<sha256>.txt``. Quando o txt
    aparece, esta função parsea e cacheia em
    ``data/output/opus_ocr_cache/<sha256>.json``.

    Modo produção (futuro, gated por env var OPUS_API_KEY):
    chama Anthropic API direto.
    """
```

### Cache canônico

Por sha256, persistido em disco. Idempotente. Se cache existe, retorna direto sem nova leitura.

## Validação DEPOIS

```bash
python -c "from src.extractors.opus_visao import extrair_via_opus; from pathlib import Path; d = extrair_via_opus(Path('tests/fixtures/opus_ocr/cupom_demo.jpeg')); print(len(d['itens']), d['total'])"
make lint && make smoke
.venv/bin/pytest tests/ -k opus_visao -q
```

## Critério de aceitação

1. `src/extractors/opus_visao.py` exporta `extrair_via_opus`.
2. Schema documentado em `mappings/schema_opus_ocr.json`.
3. Cache funcional (segunda chamada não invoca novo OCR).
4. 3 fixtures `tests/fixtures/opus_ocr/*.jpeg` com extração esperada documentada.
5. Lint + smoke + pytest baseline.

## Referência

- Auditoria: `docs/auditorias/VALIDACAO_END2END_2026-05-08.md` caso 2.
- ADR-13 (supervisor artesanal).
- ADR-26 sugerido nesta sprint: "Opus como OCR canônico para imagens".

*"Onde modelo fraco erra, modelo forte vê com olho humano." — princípio INFRA-OCR-OPUS-VISAO*
