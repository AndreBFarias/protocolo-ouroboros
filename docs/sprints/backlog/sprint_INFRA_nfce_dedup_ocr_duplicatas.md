---
id: INFRA-NFCE-DEDUP-OCR-DUPLICATAS
titulo: Extrator NFCe gera múltiplos nodes para o mesmo cupom físico — implementar dedup tolerante a OCR
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/VALIDACAO_ARTESANAL_NFCE_2026-05-12.md -- 4 nodes no grafo para 2 NFCe físicas; OCR fallback gera chave_44 alternativa quando o mesmo PDF eh processado duas vezes ou em paginas diferentes.  <!-- noqa: accent -->
---

# Sprint INFRA-NFCE-DEDUP-OCR-DUPLICATAS

## Contexto

Validação artesanal NFCe 2026-05-12 detectou 4 nodes no grafo SQLite para apenas 2 NFCe físicas:

| node_id | chave_44 | itens | total | corresponde a |
|---|---|---|---|---|
| 7680 | 53260400776574016079653040000432591876543210 | 31 (completo) | 595.52 | NFCe Supermercado 43259 |
| 7715 | 53260400776574016079653040000432591442916866 | 14 (parcial) | 595.52 | NFCe Supermercado 43259 (OCR ruim) |
| 7714 | 53260400778574016079653040000432601059682510 | 2 (PS5+P55) | 629.98 | NFCe Compra 43260 |
| 7679 | 53260400776574016079653040000432601123456788 | 2 (variante) | 629.98 | NFCe Compra 43260 (OCR alt) |

Padrão: cada NFCe real virou 2 nodes com chave_44 que diferem em **≤4 dígitos no meio** — sinal claro de OCR confundindo dígitos em zonas borradas/baixa nitidez.

## Objetivo

1. **Diagnóstico**: identificar exatamente onde no pipeline NFCe a chave_44 é gerada duas vezes (provavelmente `_extrair_chave_44` em `src/extractors/nfce_pdf.py:363` rodando em 2 contextos).
2. **Dedup tolerante**: implementar função `_eh_mesma_nfce(chave_a, chave_b, total_a, total_b, data_a, data_b) -> bool` que retorna True quando:
   - Diferença em chave_44 ≤ 4 dígitos.
   - Total idêntico (R$ 0,00 diff).
   - Data idêntica.
   - Emitente CNPJ idêntico.
3. **Aplicação no ingestor**: antes de criar node, checar se já existe outro `documento` que satisfaz `_eh_mesma_nfce`. Se sim, fundir (escolher o que tem **mais itens com qtde>0**).
4. **Limpeza retroativa**: rotina `scripts/dedup_nfce_grafo.py` que aplica regra nos 4 nodes existentes e remove os 2 redundantes (com fusão de arestas).
5. Testes em `tests/test_nfce_dedup.py` (mínimo 6).

## Validação ANTES

```bash
sqlite3 data/output/grafo.sqlite "
SELECT json_extract(metadata,'\$.chave_44') as chave, count(*) as n, group_concat(id, ',')
FROM node
WHERE tipo='documento' AND json_extract(metadata,'\$.tipo_documento')='nfce_modelo_65'
GROUP BY substr(chave, 1, 30)
HAVING n > 1
"
```

## Não-objetivos

- NÃO descartar o node com OCR pior antes de fundir arestas (perder itens é pior que duplicar).
- NÃO mexer em outros tipos de documento (cupom_fiscal_foto, holerite) — escopo restrito a NFCe.
- NÃO criar regra de fuzzy match para texto livre (apenas dígitos da chave_44 com tolerância pequena).

## Critério de aceitação

1. `_eh_mesma_nfce` implementada com 4 critérios duros (chave ≤4 diff + total exato + data exato + CNPJ exato).
2. Ingestor passa a fundir nodes em vez de duplicar.
3. `scripts/dedup_nfce_grafo.py` corrige os 4 nodes existentes para 2.
4. Pytest baseline cresce ≥ +6.
5. Pacote dashboard (cluster Documentos) mostra contagem correta de NFCe (2 visíveis, não 4).
6. Make lint exit 0. Make smoke 10/10.

## Referência

- Auditoria: `docs/auditorias/VALIDACAO_ARTESANAL_NFCE_2026-05-12.md`
- Extrator: `src/extractors/nfce_pdf.py::ExtratorNfcePDF` (linha 167) e `_extrair_chave_44` (linha 363)
- Ingestor: `src/graph/ingestor_documento.py` (verificar)
- Sprint relacionada: INFRA-DEDUP-CLASSIFICAR (já concluída, mas só para cupom; agora extensão pra NFCe)

*"Quatro nodes para duas notas eh dashboard mentiroso disfarcado de granularidade." -- principio INFRA-NFCE-DEDUP-OCR-DUPLICATAS*
