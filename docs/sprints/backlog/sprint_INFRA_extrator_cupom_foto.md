---
id: INFRA-EXTRATOR-CUPOM-FOTO
titulo: Extrator dedicado para cupom_foto JPEG (pré-processamento + Opus + parser de itens)
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: [INFRA-OCR-OPUS-VISAO]
esforco_estimado_horas: 8
origem: docs/auditorias/VALIDACAO_END2END_2026-05-08.md (cupom_foto 0/5 processados)
mockup: novo-mockup/mockups/10-validacao-arquivos.html <!-- noqa: accent -->
---

# Sprint INFRA-EXTRATOR-CUPOM-FOTO — pipeline produtivo de cupom JPEG

## Contexto

Tipo `cupom_fiscal_foto` está declarado em `mappings/tipos_documento.yaml` mas o extrator dedicado não está produtivo. 5 JPEGs em `data/raw/casal/nfs_fiscais/cupom_foto/` aguardam processamento. Tendência crescer (cliente promete enviar mais cupons via foto).

Esta sprint cria o extrator end-to-end usando Opus visão (INFRA-OCR-OPUS-VISAO).

## Objetivo

1. Criar `src/extractors/cupom_foto.py` com função pública `extrair(caminho_jpeg) -> ResultadoExtracao`.
2. Pipeline:
   - Pré-processamento (deskew, contrast normalization) via Pillow/OpenCV opcional.
   - Chamar `opus_visao.extrair_via_opus(caminho)` para obter schema canônico.
   - Validar contra `mappings/schema_opus_ocr.json`.
   - Persistir em grafo: node `documento` (sha256) + nodes `item` (1 por item) + edges `contem_item` + edge `emitida_por` (fornecedor canonizado).
3. Garantir conformance com gate D7 (`make conformance-cupom_foto >=3 amostras`).

## Validação ANTES

```bash
ls src/extractors/cupom_foto.py 2>&1
ls data/raw/casal/nfs_fiscais/cupom_foto/
grep -n "cupom_fiscal_foto" mappings/tipos_documento.yaml
```

## Não-objetivos

- NÃO duplicar lógica de OCR (delegar a INFRA-OCR-OPUS-VISAO).
- NÃO catalogar item sem código de barras (EAN); fallback `codigo_inferido` baseado em descrição+CNPJ.
- NÃO inventar valor quando OCR retorna confiança <70% — flag `revisar_humano`.

## Proof-of-work

```bash
.venv/bin/python -c "
from src.extractors.cupom_foto import extrair
r = extrair('data/raw/casal/nfs_fiscais/cupom_foto/CUPOM_2e43640d.jpeg')
print(f'Total: R$ {r.total:.2f}, Itens: {len(r.itens)}, Estabelecimento: {r.estabelecimento}')
# Esperado: Total: R$ 513.31, Itens: 52, Estabelecimento: Comercial NSP LTDA
"
make conformance-cupom_foto    # esperado: 3 amostras OK
make lint && make smoke
.venv/bin/pytest tests/ -k cupom_foto -q
```

## Critério de aceitação

1. `extrair(caminho)` retorna 52 itens para `CUPOM_2e43640d.jpeg` (validado contra leitura humana).
2. Estabelecimento "Comercial NSP LTDA" + CNPJ `56.525.495/0004-70` corretos.
3. Total R$ 513,31 corresponde à soma dos 52 itens.
4. Conformance D7: 3 amostras verdes.
5. Lint + smoke + pytest baseline.

## Referência

- Auditoria: `VALIDACAO_END2END_2026-05-08.md` caso 2 (referência canônica de output esperado).
- Sprint dependente: `INFRA-OCR-OPUS-VISAO`.

*"Extrator é prova de pipeline funcionar. Sem amostra real, é só intenção." — princípio INFRA-EXTRATOR-CUPOM-FOTO*
