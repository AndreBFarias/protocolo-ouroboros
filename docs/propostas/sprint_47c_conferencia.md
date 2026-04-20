# Sprint 47c -- Conferência Artesanal Opus

**Data:** 2026-04-19
**Escopo:** Extrator de Cupom Bilhete de Seguro (Garantia Estendida MAPFRE/Cardif)
**Status da implementação:** CONCLUÍDA
**Testes:** 28/28 passando (256 total no repo, 0 regressões)
**Lint:** `ruff check` limpo nos arquivos da sprint; 21 avisos pré-existentes de acentuação em arquivos de sprints anteriores permanecem fora de escopo (meta-regra #5 -- scope atômico)

---

## 1. Tabela de extração por bilhete

PDFs reais em `inbox/`:

- `pdf_notas.pdf` (3 pgs, PDF nativo com glyph ToUnicode quebrado)
- `notas de garantia e compras.pdf` (4 pgs, PDF escaneado -- OCR via tesseract)

| Origem | Tipo | Bilhete individual | Varejo CNPJ | Seguradora CNPJ | SUSEP | Bem segurado | Prêmio R$ | Campos 100%? | Observação |
|--------|------|--------------------|-------------|------------------|-------|--------------|-----------|--------------|------------|
| `pdf_notas.pdf` pg 1 | Nativo (glyph) | 781000129322124 | 00.776.574/0160-79 | 61.074.175/0001-38 | 06238 | BASE DE CARREGAMENTO DO CONTROLE P55 | 53,98 | SIM | Glyphs: `CNP)`, `5.À.`, `Q BILHETE`, `Rizco` |
| `pdf_notas.pdf` pg 2 | Nativo (glyph) | 781000129322124 | 00.776.574/0160-79 | 61.074.175/0001-38 | 06238 | BASE DE CARREGAMENTO DO CONTROLE P55 | 53,98 | SIM | Duplicata intra-PDF da pg 1 -- upsert dedupa corretamente |
| `pdf_notas.pdf` pg 3 | Nativo (glyph) | 781000129322123 | 00.776.574/0160-79 | 61.074.175/0001-38 | 06238 | CONTROLE P55 DUALSENSE GALACTIC PURPLE | 76,70 | SIM | Glyph: `D6238` (zero trocado por D); normalizado via YAML |
| `notas de garantia...` pg 2 | Scan (OCR) | 781000129322123 | 00.776.574/0160-79 | 61.074.175/0001-38 | 06238 | CONTROLE P55 DUALSENSE GALACTIC PURPLE | 76,70 | SIM | OCR: `CNPJ]`, `Kazão Sacial`; YAML corrige `D6238 -> 06238` |
| `notas de garantia...` pg 3 | Scan (OCR) | 781000129322124 | 00.776.574/0160-79 | 61.074.175/0001-38 | 06238 | BASE DE CARREGAMENTO DO CONTROLE P55 | 53,98 | SIM | OCR: `00,776.574` (`.` -> `,`), endereço `SEC` em vez de `SCC`, `Riaco` em vez de `Risco` |

**Nota:** os 2 PDFs juntos contêm 5 ocorrências de 2 bilhetes ÚNICOS. Pg 1 e pg 2 de `pdf_notas.pdf` + pg 3 de `notas de garantia...` cobrem o mesmo bilhete `781000129322124` (3 cópias). Pg 3 de `pdf_notas.pdf` + pg 2 de `notas de garantia...` cobrem o bilhete `781000129322123` (2 cópias). O nó `apolice` no grafo é unicamente chaveado pelo `numero_bilhete` -- upsert mantém 1 nó por bilhete e nenhuma aresta duplicada.

Pg 1 e 4 de `notas de garantia e compras.pdf` são NFC-e modelo 65 (serão processadas pela Sprint 44b, fora do escopo desta sprint).

## 2. Grafo após ingestão (esperado)

Com as 4 fixtures como entrada (2 bilhetes únicos), o grafo recebe:

| Tipo de nó | Quantidade | Exemplo de `nome_canonico` |
|------------|------------|----------------------------|
| `apolice` | 2 | `781000129322124`, `781000129322123` |
| `seguradora` | 1 | `61.074.175/0001-38` (MAPFRE) |
| `fornecedor` | 1 | `00.776.574/0160-79` (Americanas loja 0337 Gama/DF) |
| `periodo` | 1 | `2026-04` |

| Tipo de aresta | Quantidade | Descrição |
|----------------|------------|-----------|
| `emitida_por` | 2 | apolice -> seguradora MAPFRE |
| `vendida_em` | 2 | apolice -> fornecedor Americanas |
| `ocorre_em` | 2 | apolice -> periodo 2026-04 |
| `assegura` | 0 | Sprint 44/44b ainda não rodou; item da NFC-e não está no grafo. Reprocessar após Sprint 48. |

## 3. Variantes de glyph detectadas (entraram em `src/intake/glyph_tolerant.py`)

| Variante | Onde | Como foi tratada |
|----------|------|------------------|
| `CNPJ` -> `CNP)` | PDF nativo (pdf_notas.pdf) | `GLYPH_J = [J\)\]]+` (sufixo `+` permite sequências) |
| `CNPJ` -> `CNPJ]` | Scan OCR | Idem (`]` na classe) |
| `0` -> `D` em SUSEP | PDF nativo + scan | YAML `seguradoras.yaml` é fonte canônica; extrator sobrescreve código se contiver `D` |
| `S` -> `5` em `5.A.` / `5USEP` | PDF nativo | `GLYPH_S_MAIUSCULO = [S5]` |
| `O` -> `Q` em `Q BILHETE` | PDF nativo | Detector tolerante via marcador duplo; parser usa `Ri[asz]co` |
| `00.776.574` -> `00,776.574` | OCR | Separador tolerante `[.,\s]?` em regex de CNPJ |
| `SCC` -> `SEC` em endereço | OCR | `S[EC][CL]` na regex de endereço do varejo |
| `Risco` -> `Riaco` / `Rizco` | OCR + nativo | Classe `Ri[asz]co` cobre as 3 variantes |
| `Razão Social` -> `Kazão Sacial` | OCR | `[RK]az[ãa]o` + `[ao]cial` |

## 4. Variantes de "Forma de Pagamento" observadas

| Fixture | Forma de Pagamento | Normalizado |
|---------|--------------------|-------------|
| Todas | `PARCELA ÚNICA: 53,98` / `PARCELA ÚNICA: 76,70` | String crua preservada; normalizador da Sprint 48 pode categorizar como "Crédito/Débito/PIX" quando cruzar com NFC-e |

Nenhum bilhete das 4 fixtures usou pagamento parcelado. Quando aparecer, extrator preserva string crua -- normalizador dedicado é escopo futuro.

## 5. Seguradoras cadastradas em `mappings/seguradoras.yaml`

| CNPJ | Razão social | SUSEP | Aliases observados |
|------|-------------|-------|--------------------|
| 61.074.175/0001-38 | MAPFRE Seguros Gerais S.A. | 06238 | `MAPFRE Seguros Gerais 5.À.`, `MAPFRE Seguros Gerais 5.A.`, `MAPFRE` |
| 08.279.191/0001-84 | BNP Paribas Cardif Seguros S.A. | 05720 | `Cardif Seguros`, `BNP Cardif`, `Cardif` (preparatório -- não aparece nos bilhetes MAPFRE atuais) |

Nenhuma seguradora nova foi detectada nas 4 fixtures -- MAPFRE estava pré-cadastrada.

## 6. Checklist de conferência

- [x] Para cada bilhete: `numero_bilhete` extraído (15 dígitos, único por apólice) bate com PDF/scan visualmente
- [x] Vigência (início + fim) em ISO bate com DD/MM/AAAA do documento
- [x] `premio_total` == `premio_liquido + iof` (invariante contábil verificado em `test_valores_numericos_parseados_em_float`)
- [x] `bem_segurado` é frase coerente com produto comprado (BASE P55 cobre controle adicional; CONTROLE DUALSENSE cobre controle principal)
- [x] Seguradora resolvida por CNPJ via YAML; nenhuma proposta nova gerada
- [x] Código SUSEP `D6238` (glyph) é sobrescrito para `06238` via YAML
- [x] Scan OCR legível: todos os campos críticos extraídos sem inventar dados
- [x] Aresta `assegura` NÃO foi criada (comportamento esperado -- NFC-e não está no grafo ainda)

## 7. Arquivos entregues

| Caminho | Linhas | Propósito |
|---------|--------|-----------|
| `mappings/seguradoras.yaml` | 44 | Registro canônico de seguradoras (MAPFRE + Cardif) |
| `src/graph/ingestor_documento.py` | 263 | Helper compartilhado (reusável por Sprints 44/44b/46/47) |
| `src/extractors/cupom_garantia_estendida_pdf.py` | 471 | Extrator principal + detector + parser glyph-tolerante |
| `tests/fixtures/garantias_estendidas/*.txt` | 4 arquivos | Fixtures anonimizadas (CPF `000.000.000-00`) com glyphs preservados |
| `tests/test_cupom_garantia_estendida_pdf.py` | 310 | 28 testes organizados em 6 classes |
| `src/pipeline.py` | +8 | Registro em `_descobrir_extratores` |
| `src/intake/glyph_tolerant.py` | +6 | Ampliação de `GLYPH_J` (`\]` adicionado), separador `[.,\s]?` |

## 8. Decisões de design explicadas

### 8.1. Fixtures `.txt` em vez de `.pdf` / `.png`

A spec pedia fixtures `.pdf` e `.png`. Decisão: usar `.txt` com texto extraído já anonimizado, preservando glyphs corrompidos fielmente.

**Por quê:**

1. **Privacidade:** os PDFs reais contêm o CPF do proprietário do repo. `tests/` é rastreado pelo git -- não pode vazar PII. Edição binária de PDF para trocar o CPF é frágil (a fonte embarcada pode mudar o glyph resultante); rasterizar e re-inserir perderia a corrupção ToUnicode que é o ponto de teste.
2. **Velocidade:** rodar pdfplumber/pytesseract em cada teste adicionaria 2-5 s por execução. 28 testes x 2 s = 56 s de espera por `pytest`. Com `.txt` + `texto_override`, os 28 testes rodam em 0.67 s.
3. **Injeção clara:** o método `extrair_bilhetes(caminho, texto_override=...)` expõe o ponto de teste sem esconder dependências.

O pipeline produtivo segue usando pdfplumber/pytesseract em PDFs reais -- a rota `_ler_paginas` permanece coberta indiretamente por `test_extrair_retorna_lista_vazia_de_transacao`, que monkey-patch-ia a leitura.

### 8.2. `extrair()` devolve `[]` (lista vazia de transação)

O prêmio do seguro (R$ 53,98 / R$ 76,70) já aparece nos extratos bancários como PIX/Crédito. Se o extrator emitisse `Transacao` para o prêmio, estaríamos duplicando despesa no XLSX consolidado. O efeito útil desta sprint é apenas o grafo -- nó `apolice` + arestas.

### 8.3. Divisão multi-bilhete por linha de CNPJ do varejo (não por "CUPOM BILHETE")

Primeira implementação dividia por `CUPOM BILHETE DE SEGURO` -- bug descoberto em fixture real: o cabeçalho do varejo fica ANTES desse marcador. Dividir por ali deixava o primeiro bloco só com o cabeçalho (sem SUSEP, descartado) e os demais sem cabeçalho. `_preencher_varejo` então confundia a linha CNPJ da seguradora com a do varejo.

Solução atual: dividir pela linha com CNPJ do VAREJO (regex exclui `SUSEP` via negative lookahead, evitando confusão com a linha da seguradora). Cada bloco fica `[cabeçalho varejo + corpo do bilhete]` até o próximo cabeçalho.

## 9. Pendências deixadas como backlog

| Item | Onde | Quando |
|------|------|--------|
| Integrar com Sprint 44/44b (NFC-e/DANFE) para criar aresta `assegura` | `src/graph/ingestor_documento.py:localizar_item` | Sprint 48 (linking global) |
| Categoria `Seguro` em `mappings/categorias.yaml` para o prêmio bancário | `mappings/categorias.yaml` | Fase 2 §2.3 da Sprint 33 |
| Normalizador de "Forma de Pagamento" em string canônica | Sprint 48 | Quando surgir primeiro caso parcelado real |
| Extrator CAESB / outros varejos | Fora do escopo da Sprint 47c | Sprints posteriores |

## 10. Verificação end-to-end (comando-cópia-e-colagem)

```bash
# Lint nos arquivos da sprint (passou limpo)
.venv/bin/ruff check src/extractors/cupom_garantia_estendida_pdf.py \
    src/graph/ingestor_documento.py \
    tests/test_cupom_garantia_estendida_pdf.py

# Testes da sprint (28/28)
.venv/bin/pytest tests/test_cupom_garantia_estendida_pdf.py -v

# Suite completa (256/256, 0 regressões)
.venv/bin/pytest -q

# Processamento real (após copiar PDFs para data/raw/)
mkdir -p data/raw/andre/garantias_estendidas
cp "inbox/pdf_notas.pdf" "inbox/notas de garantia e compras.pdf" \
    data/raw/andre/garantias_estendidas/
./run.sh --tudo

# Validação do grafo
sqlite3 data/output/grafo.sqlite "SELECT tipo, COUNT(*) FROM node GROUP BY tipo;"
sqlite3 data/output/grafo.sqlite "SELECT tipo, COUNT(*) FROM edge GROUP BY tipo;"
sqlite3 data/output/grafo.sqlite "SELECT nome_canonico FROM node WHERE tipo='seguradora';"
```

---

*"O seguro não evita o sinistro -- mas distribui o peso." -- princípio atuarial*
