---
id: INFRA-NFCE-FIX-PS5-P55
titulo: Corrigir bug confirmado — item "BASE DE CARREGAMENTO DO CONTROLE P55" deve ser "PS5"
status: concluida
concluida_em: 2026-05-12
prioridade: P1
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: []
esforco_estimado_horas: 1
origem: docs/auditorias/VALIDACAO_ARTESANAL_NFCE_2026-05-12.md -- confronto multimodal PDF-real × grafo confirmou que OCR fallback escreveu "P55" em vez de "PS5" no item EAN 000004298119 (Base Carregamento Controle PS5). Outro item PS5 (CONTROLE PS5 DUALSENSE, EAN 000004300823) ficou correto.  <!-- noqa: accent -->
---

# Sprint INFRA-NFCE-FIX-PS5-P55

## Contexto

Validação artesanal NFCe 2026-05-12 (cupom PS5 da Americanas, 19/04/2026 17:12) revelou que o item canônico no grafo é:

- `BASE DE CARREGAMENTO DO CONTROLE P55` (errado)

quando o cupom físico de alta resolução diz:

- `BASE DE CARREGAMENTO DO CONTROLE PS5` (correto)

Cobertura de garantia estendida na página 3 do PDF confirma o produto: "Descrição do bem segurado: BASE DE CARREGAMENTO DO CONTROLE PS5".

O outro item PS5 do mesmo cupom (EAN 000004300823, "CONTROLE PS5 DUALSENSE GALACTIC PURPLE") foi capturado corretamente. Apenas EAN 000004298119 caiu no typo OCR (S/5 confusão).

## Objetivo

1. Localizar nodes no grafo SQLite com `nome_canonico` ou `metadata.descricao` contendo "P55" no contexto de produtos PS5.
2. Aplicar correção: trocar "P55" por "PS5" quando contexto for produto Sony PlayStation 5 (palavras adjacentes: CONTROLE, BASE, DUALSENSE, JOGO, PLAYSTATION).
3. Adicionar regra de normalização preventiva em `src/intake/glyph_tolerant.py` (já existe módulo) para confusão S/5 em contextos específicos.
4. Re-rodar `processar_inbox_massa` ou rotina de re-extração nos 2 PDFs Americanas para validar que regra previne reincidência.
5. Teste regressivo em `tests/test_glyph_tolerant.py` + `tests/test_nfce_pdf.py`.

## Validação ANTES

```bash
sqlite3 data/output/grafo.sqlite "SELECT id, nome_canonico, substr(metadata,1,200) FROM node WHERE tipo='item' AND (metadata LIKE '%P55%' OR nome_canonico LIKE '%P55%')"
grep -rn "P55\|PS5" src/intake/glyph_tolerant.py | head
```

## Não-objetivos

- NÃO modificar EAN 000004298119 — código de barras é literal do produto.
- NÃO converter TODA ocorrência de "P55" para "PS5" sem checar contexto (poderia haver produto Honda P55 ou outro).
- NÃO retocar nodes que já estão corretos.

## Critério de aceitação

1. Node com "BASE DE CARREGAMENTO DO CONTROLE P55" passa para "PS5".
2. Regra preventiva em `glyph_tolerant.py` aplica `re.sub(r'\bP55\b(?=.*(CONTROLE|PS|PLAYSTATION|SONY))', 'PS5', texto)` (ou estratégia equivalente).
3. Teste regressivo: feed do texto OCR original "BASE DE CARREGAMENTO DO CONTROLE P55" produz "PS5" após normalização.
4. Pytest baseline cresce ≥ +2.
5. Make lint exit 0. Make smoke 10/10.

## Referência

- Auditoria: `docs/auditorias/VALIDACAO_ARTESANAL_NFCE_2026-05-12.md`
- Grafo: `data/output/grafo.sqlite` node id 7714 (chave_44 ...432601059682510)
- PDF: `data/raw/andre/nfs_fiscais/nfce/NFCE_2026-04-19_6c1cc203.pdf` página 1 (item 2)
- Garantia confirma: página 3 do mesmo PDF

*"Bug confirmado por confronto multimodal vale 100 hipoteses; nao adia." -- principio INFRA-NFCE-FIX-PS5-P55*
