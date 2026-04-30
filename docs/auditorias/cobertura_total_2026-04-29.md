# Auditoria de cobertura total D7 (2026-04-29)

> Sprint META-COBERTURA-TOTAL-01. Gerada por `python scripts/auditar_cobertura_total.py --executar`.

- Extratores em `src/extractors/`: **20**
- Violações no lint estático: **0**
- Tipos de documento no grafo: **4**

## Lint estático

Sem violações detectadas pelo lint estático.

## Cobertura no grafo (snapshot)

| Tipo de documento | Documentos | Com `documento_de` | Com `contem_item` |
|---|---:|---:|---:|
| boleto_servico | 2 | 0 | 0 |
| das_parcsn_andre | 19 | 5 | 0 |
| holerite | 24 | 20 | 0 |
| nfce_modelo_65 | 2 | 0 | 2 |

## Extratores em src/extractors/

Lista canônica para a Sprint RETRABALHO-EXTRATORES-01 ramificar em tiers A/B/C/D:

- `boleto_pdf.py`
- `c6_cartao.py`
- `c6_cc.py`
- `contracheque_pdf.py`
- `cupom_garantia_estendida_pdf.py`
- `cupom_termico_foto.py`
- `danfe_pdf.py`
- `das_parcsn_pdf.py`
- `dirpf_dec.py`
- `energia_ocr.py`
- `garantia.py`
- `itau_pdf.py`
- `nfce_pdf.py`
- `nubank_cartao.py`
- `nubank_cc.py`
- `ofx_parser.py`
- `receita_medica.py`
- `recibo_nao_fiscal.py`
- `santander_pdf.py`
- `xml_nfe.py`

## Próximos passos

1. Cada extrator listado acima passa por triagem na Sprint RETRABALHO-EXTRATORES-01.
2. Se o lint detectar nova violação no futuro, abrir sprint-filha `sprint_retrabalho_<extrator>.md` na hora -- regra zero TODO solto.
3. Comparar este snapshot com auditorias anteriores em `docs/auditorias/cobertura_total_*.md` para detectar regressões.

*"Saber a cobertura é metade da cobertura. Agir sobre ela é a outra metade." -- princípio do auditor.*
