<!-- noqa: accent -->
---
id: INFRA-EXTRATORES-USAR-OPUS
titulo: Refatorar 5 extratores que falham com campos_insuficientes para usar extrair_via_opus como fallback
status: backlog
prioridade: altissima
data_criacao: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: [INFRA-OCR-OPUS-VISAO]
esforco_estimado_horas: 6
origem: investigação fim-a-fim 2026-05-08 — log do reprocessar_documentos.py mostra 5 cupom_termico_foto + 8 garantia + 3 receita + 3 danfe FALHAM por OCR fraco (campos_insuficientes). Solução: chamar extrair_via_opus quando OCR local falha.
---

# Sprint INFRA-EXTRATORES-USAR-OPUS — fallback Opus em extratores específicos

## Contexto

Validação fim-a-fim 2026-05-08 + execução de `reprocessar_documentos.py` revelaram que extratores específicos (cupom_termico_foto, cupom_garantia_estendida_pdf, danfe_pdf, receita_medica, nfce_pdf parcialmente) **falham com `campos_insuficientes`** porque dependem do OCR local fraco. Resultado: 0 nodes ingeridos para cupom_foto e garantia apesar de existirem 5+8 arquivos brutos.

INFRA-OCR-OPUS-VISAO (commit `d7f8805`) já deu a solução: função `extrair_via_opus(caminho)` retorna schema canônico via Opus multimodal (modo supervisor artesanal ADR-13).

Esta sprint refatora os 5 extratores para usar Opus como fallback.

## Objetivo

Em cada extrator afetado:
1. Tentar OCR local primeiro (mantém retrocompat).
2. Se resultado tem `erro=campos_insuficientes` OU campos críticos vazios, chamar `extrair_via_opus(caminho)`.
3. Mapear schema canônico Opus para schema interno do extrator.
4. Log estruturado: qual modo usou (`local` ou `opus`), confiança final.

Extratores afetados:
- `src/extractors/cupom_termico_foto.py` (5 cupons em `data/raw/casal/nfs_fiscais/cupom_foto/`)
- `src/extractors/cupom_garantia_estendida_pdf.py` (8 garantias)
- `src/extractors/danfe_pdf.py` (5 danfe NFe55)
- `src/extractors/receita_medica.py` (3 receitas)
- `src/extractors/nfce_pdf.py` (NFCe que ainda não caem em fallback)

## Validação ANTES (grep — padrão `(k)`)

```bash
grep -n "campos_insuficientes\|return.*erro" src/extractors/cupom_termico_foto.py src/extractors/cupom_garantia_estendida_pdf.py src/extractors/danfe_pdf.py src/extractors/receita_medica.py src/extractors/nfce_pdf.py | head -10
ls data/output/opus_ocr_cache/ | head
```

## Não-objetivos

- NÃO modificar `extrair_via_opus` (já está produtivo).
- NÃO chamar Anthropic API automaticamente nesta sprint (mantém ADR-13 — supervisor artesanal preenche cache).
- NÃO refatorar extratores que já funcionam (holerite, das_parcsn, boleto_servico).

## Spec de implementação

Cada extrator afetado ganha bloco padrão:

```python
def _extrair_local(self, caminho: Path) -> dict:
    """OCR local atual (retrocompat)."""
    # ... existing code ...

def _extrair_via_opus_fallback(self, caminho: Path) -> dict:
    """Fallback via Opus multimodal."""
    from src.extractors.opus_visao import extrair_via_opus
    payload = extrair_via_opus(caminho)
    return self._mapear_schema_canonico(payload)

def extrair(self, caminho: Path) -> dict:
    resultado = self._extrair_local(caminho)
    if resultado.get("erro") == "campos_insuficientes":
        logger.info("Extrator local falhou; tentando Opus para %s", caminho.name)
        return self._extrair_via_opus_fallback(caminho)
    return resultado
```

Cada classe implementa `_mapear_schema_canonico(payload_opus) -> schema_interno`.

## Proof-of-work (padrão `(u)`)

```bash
# 1. Cache canônico do cupom 2e43640d (existe via INFRA-OCR-OPUS-VISAO)
ls data/output/opus_ocr_cache/2e43640d*.json

# 2. Extrator cupom_termico_foto agora ingere via fallback Opus
.venv/bin/python -c "
from src.extractors.cupom_termico_foto import ExtratorCupomTermicoFoto
from pathlib import Path
e = ExtratorCupomTermicoFoto()
r = e.extrair(Path('data/raw/casal/nfs_fiscais/cupom_foto/CUPOM_2e43640d.jpeg'))
print(f'Total: R\$ {r[\"total\"]:.2f}, Itens: {len(r[\"itens\"])}')
# Esperado: Total: R\$ 513.31, Itens: 52
"

# 3. Reprocessar com flag forçar
python scripts/reprocessar_documentos.py --forcar-reextracao
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='documento'"
# Esperado: passar de 48 para >=60

make lint && make smoke
.venv/bin/pytest tests/ -k "cupom or garantia or danfe or receita or nfce" -q
```

## Critério de aceitação

1. 5 extratores afetados implementam fallback Opus.
2. Cupom 2e43640d ingere com 52 itens + R$ 513,31 (validação canônica).
3. `reprocessar_documentos.py --forcar-reextracao` aumenta nodes `documento` de 48 para >=60.
4. Cache `data/output/opus_ocr_cache/` cresce (sem requerir API direta — preenchido manualmente via supervisor artesanal).
5. Lint + smoke + pytest baseline.

## Referência

- Sprint dependente: `INFRA-OCR-OPUS-VISAO` (commit `d7f8805`).
- Log canônico do problema: `tail -n 100 /tmp/claude-1000/.../tasks/bi80mmwmy.output` (5 cupons cupom_termico_foto, 8 garantias falharam).
- Auditoria: `VALIDACAO_END2END_2026-05-08.md`.

*"Modelo forte cobre buraco do modelo fraco." — princípio INFRA-EXTRATORES-USAR-OPUS*
