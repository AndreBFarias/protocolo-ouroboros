---
concluida_em: 2026-04-20
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 47c
  title: "Extrator de Cupom Bilhete de Seguro (Garantia Estendida MAPFRE/Cardif)"
  touches:
    - path: src/extractors/cupom_garantia_estendida_pdf.py
      reason: "extrai cabeçalho (varejo + seguradora + bilhete + processo SUSEP) e dados da apólice (bem segurado, prêmio, vigência, cobertura) de PDF/imagem de Bilhete de Seguro de Garantia Estendida"
    - path: src/graph/ingestor_documento.py
      reason: "estende ingestor compartilhado (Sprint 44) para criar nó Apolice + Seguradora + aresta `assegura` para Item já existente no grafo (do NFC-e/DANFE pareado)"
    - path: mappings/seguradoras.yaml
      reason: "registra seguradoras conhecidas (CNPJ, código SUSEP, nome canônico) para entity resolution rápida"
    - path: mappings/tipos_documento.yaml
      reason: "tipo cupom_garantia_estendida já registrado pela Sprint 41; aqui apenas confirma e adiciona campos extraídos pelo extrator"
    - path: src/pipeline.py
      reason: "registra ExtratorCupomGarantiaEstendida em _descobrir_extratores"
    - path: tests/fixtures/garantias_estendidas/
      reason: "fixtures: 5 bilhetes reais anonimizados extraídos dos PDFs da inbox (3 do pdf_notas.pdf, 2 das pgs 2-3 de notas de garantia e compras.pdf)"
  n_to_n_pairs:
    - [src/extractors/cupom_garantia_estendida_pdf.py, src/graph/ingestor_documento.py]
    - [mappings/seguradoras.yaml, src/extractors/cupom_garantia_estendida_pdf.py]
  forbidden:
    - src/extractors/garantia_pdf.py  # Sprint 47b cobre Termo de Garantia do FABRICANTE; é outro tipo. NÃO duplicar.
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_cupom_garantia_estendida_pdf.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Extrai >= 4 bilhetes de seguro (variantes: PDF nativo com fonte boa, PDF nativo com fonte ToUnicode quebrada, scan via OCR, e cupom de outro varejo se disponível) com 100% dos campos canônicos preenchidos"
    - "Número do bilhete individual extraído como identificador único (15 dígitos) e usado como chave canônica do nó Apolice"
    - "Processo SUSEP extraído no formato XXXXX.XXXXXX/XXXX-XX"
    - "Vigência (início + fim) e cobertura de risco (início + fim) extraídas como datas ISO"
    - "Seguradora resolvida via mappings/seguradoras.yaml (CNPJ é a chave); cadastro novo gera proposta em docs/propostas/seguradoras/"
    - "Grafo recebe: 1 Apolice + 1 Seguradora + 1 Varejo + arestas `emitida_por` (Apolice→Seguradora), `vendida_em` (Apolice→Varejo); aresta `assegura` (Apolice→Item) só existe se Sprint 48 já tiver linkado o NFC-e e o Item correspondente já existir"
    - "Glyph-tolerant: parser passa contra fixture extraída de pdf_notas.pdf (CNP), 5.A., Q BILHETE) -- usa src/intake/glyph_tolerant.py"
    - "Acentuação PT-BR correta, zero emojis, zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 47c -- Extrator de Cupom Bilhete de Seguro (Garantia Estendida)

**Status:** CONCLUÍDA
**Aprovação:** aprovada em 2026-04-19 -- ver `docs/propostas/sprint_nova/sprint_47c_cupom_garantia_estendida.md`. Implementação aguarda apenas Sprint 41 e 42 concluírem (dependências declaradas)
**Data:** 2026-04-19 (criada na Conferência Artesanal Opus da Sprint 41)
**Prioridade:** MEDIA (volume real observado: 5 bilhetes em 1 dia de inbox)
**Tipo:** Feature
**Dependências:** Sprint 41 (intake roteia para `garantias_estendidas/`), Sprint 42 (grafo recebe nó `Apolice` + `Seguradora`)
**Desbloqueia:** Sprint 48 (linking NFC-e ↔ Apólice via Item compartilhado é caso de teste de ouro)
**Issue:** --
**ADR:** ADR-14 (grafo extensível), ADR-15 (intake multiformato)

---

## Como Executar

- `.venv/bin/pytest tests/test_cupom_garantia_estendida_pdf.py -v`
- `./run.sh --tudo` -- extrator roda no pipeline e popula grafo

### O que NÃO fazer

- NÃO confundir com Termo de Garantia do fabricante (Sprint 47b). Documentos legalmente distintos: termo é cobertura de defeito, bilhete é apólice de seguro regulada pela SUSEP.
- NÃO categorizar o prêmio como "Eletrônicos" ou similar -- o prêmio é despesa de tipo `Seguro` (categoria nova a propor em `mappings/categorias.yaml` quando Sprint 48 cruzar com a transação bancária).
- NÃO inferir vigência -- ela está explícita no documento; se não bater regex, falhar com warning, não chutar.
- NÃO criar nó `Item` aqui -- o item segurado já existe no grafo via NFC-e/DANFE da Sprint 44/44b. Esta sprint apenas adiciona aresta `assegura` quando o item está localizável.

---

## Problema

Bilhetes de seguro de garantia estendida são apólices SUSEP emitidas no PDV no momento da compra. O sistema hoje não os reconhece -- vão direto para `_classificar/`. Volume real observado em 2026-04-19: **5 bilhetes em 2 PDFs** da inbox (3 no `pdf_notas.pdf`, 2 nas pgs 2-3 de `notas de garantia e compras.pdf`).

Sem extrator dedicado:

1. O custo do prêmio fica descolado da compra original (R$ 53,98 + R$ 76,70 vs nota R$ 629,98 -- são despesas relacionadas que precisam ser cruzáveis).
2. A vigência de cobertura não é monitorada -- usuário pode pagar por garantia que já expirou.
3. Não há rastro de quem é a seguradora (importante para acionamento de sinistro).
4. Não há base para cruzar com bilhetes futuros (recompra de seguro, renovação, sinistro).

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Ingestor de documento | `src/graph/ingestor_documento.py` (criado pela 44) | Insere Documento + Itens + Fornecedor + arestas. Estender para nó `Apolice` em vez de `Documento`. |
| Glyph tolerant | `src/intake/glyph_tolerant.py` (criado pela 41) | Regex tolerante a fonte ToUnicode quebrada. **Reusar.** |
| Validação de CNPJ | `src/transform/irpf_tagger.py:_REGEX_CNPJ` | Reusar (com versão tolerante da 41). |
| Pessoa via CPF | (Sprint 41 fase 3) | Detecção de pessoa via CPF do segurado. |
| Sprint 47b (Termo de Garantia) | `src/extractors/garantia_pdf.py` (futuro) | Tipo distinto. NÃO compartilhar parser. |

## Implementação

### Fase 1: detector específico

`_e_cupom_garantia_estendida(texto: str) -> bool`:

Casa pelo menos 2 de 3 (com tolerância a glyphs):
- `r"CUPOM\s+[B8]ILHETE\s+DE\s+SEGURO"`
- `r"GARANTIA\s+ESTENDIDA"`
- `r"Processo\s+[S5]USEP"`

### Fase 2: parser dos campos canônicos

`_parse_bilhete(texto: str) -> dict`:

Campos obrigatórios:
- `numero_bilhete`: `r"BILHETE\s+INDIVIDUAL[:\s]+(\d{12,18})"` -- chave canônica
- `processo_susep`: `r"[S5]USEP\s+No?\.?\s*([\d./\-]+)"`
- `cpf_segurado`: `r"CPF[:\s]+([\d.\s\-]{11,16})"` -- normalizar removendo espaços (Armadilha #20: pdf_notas tem `051.273. 731-22` e `051.273.2731-22` por glyph)
- `bem_segurado`: `r"Descri[çc][ãa]o.*?segurado.*?\)?:?\s*\n?(.+?)\n"`
- `valor_bem`: `r"Limite\s+M[áa]ximo.*?:\s*([\d.,]+)"`
- `premio_liquido`: `r"PR[ÊE]MIO\s+L[ÍI]QUIDO[:\s]+([\d.,]+)"`
- `iof`: `r"IOF[:\s]+([\d.,]+)"`
- `premio_total`: `r"PR[ÊE]MIO\s+TOTAL[:\s]+([\d.,]+)"`
- `vigencia_inicio`, `vigencia_fim`: regex para "Início/Fim de Vigência de Contrato"
- `cobertura_inicio`, `cobertura_fim`: regex para "Início/Fim de Cobertura de Risco"
- `forma_pagamento`: linha após "Forma de Pagamento:"
- `seguradora_razao_social`: `r"Raz[ãa]o\s+Social[:\s]+(.+?)\n"`
- `seguradora_cnpj`: regex CNPJ tolerante após bloco "DADOS DA SEGURADORA"
- `seguradora_codigo_susep`: `r"Cod\s+[S5]USEP[:\s]+(\d+)"`
- `varejo_razao_social`, `varejo_cnpj`, `varejo_endereco`: bloco do topo do cupom

### Fase 3: ingestão no grafo (estende ingestor da Sprint 44)

```python
def ingerir_apolice(
    db: GrafoDB,
    bilhete: dict,
    caminho_arquivo: Path,
) -> int:
    apolice_id = db.upsert_node(
        "apolice",
        bilhete["numero_bilhete"],
        metadata={**bilhete, "tipo_documento": "cupom_garantia_estendida"},
    )
    seguradora_id = db.upsert_node("seguradora", bilhete["seguradora_cnpj"], metadata={...})
    varejo_id = db.upsert_node("fornecedor", bilhete["varejo_cnpj"], metadata={...})
    db.adicionar_edge(apolice_id, seguradora_id, "emitida_por")
    db.adicionar_edge(apolice_id, varejo_id, "vendida_em")
    item_id = db.localizar_item_por_descricao_e_data(
        bilhete["bem_segurado"],
        bilhete["vigencia_inicio"],
        cnpj_varejo=bilhete["varejo_cnpj"],
    )
    if item_id:
        db.adicionar_edge(apolice_id, item_id, "assegura",
                          evidencia={"match": "descricao+data+varejo"})
    return apolice_id
```

`localizar_item_por_descricao_e_data` é heurístico (rapidfuzz na descrição do bem com janela de ±1 dia da emissão); se ambíguo, registra em `docs/propostas/linking/<apolice_id>.md` e segue sem aresta `assegura` (não chuta).

### Fase 4: registro no pipeline

```python
try:
    from src.extractors.cupom_garantia_estendida_pdf import ExtratorCupomGarantiaEstendida
    extratores.append(ExtratorCupomGarantiaEstendida)
except ImportError as e:
    logger.warning("Extrator cupom_garantia_estendida_pdf indisponível: %s", e)
```

### Fase 5: testes

Fixtures em `tests/fixtures/garantias_estendidas/`:
- `bilhete_pdf_native_americanas_base_p55.pdf` (anonimizado: pgs 1-2 de pdf_notas.pdf, com fonte ToUnicode quebrada)
- `bilhete_pdf_native_americanas_controle_p55.pdf` (anonimizado: pg 3 de pdf_notas.pdf)
- `bilhete_scan_americanas_base_p55.png` (anonimizado: pg 2 de notas de garantia e compras.pdf, escaneada)
- `bilhete_scan_americanas_controle_p55.png` (anonimizado: pg 3 de notas de garantia e compras.pdf, escaneada)

Testes mínimos:
- `test_detecta_bilhete_pdf_native`
- `test_detecta_bilhete_scan_via_ocr`
- `test_glyph_tolerante_cnpj_corrompido_no_pdf_native`
- `test_extrai_15_digitos_bilhete_individual`
- `test_extrai_processo_susep_formato_canonico`
- `test_vigencia_e_cobertura_extraidas_como_datas`
- `test_seguradora_mapfre_resolvida_via_yaml`
- `test_pdf_notas_pg1_e_pg2_geram_mesmo_bilhete_id` (caso de duplicata intra-PDF -- a 41 já filtrou na pasta `_envelopes/duplicatas/`, este teste valida que se a duplicata escapar para cá, o `upsert_node` por bilhete_individual evita aresta dupla)

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A47c-1 | "Bem segurado (Modelo/Marca)" às vezes vira "Bem segurado (Modela/Marca)" por glyph | Aceitar `Model[oa]` na regex |
| A47c-2 | CPF aparece com espaço no meio (`051.273. 731-22`) | Normalizar `cpf.replace(" ", "")` antes de validar |
| A47c-3 | Código SUSEP às vezes vira `D6238` em vez de `06238` (zero vira D no glyph) | Normalizar `[D0]` no início de códigos numéricos curtos -- ou validar contra `seguradoras.yaml` por CNPJ e ignorar o código se discrepante |
| A47c-4 | "Forma de Pagamento" às vezes seguido por "PARCELA ÚNICA: R$ X" e às vezes por bloco multilinha "Cartão Crédito ... Parcelas: 3" | Extrair como string crua e normalizar via lookup; se desconhecido, gerar proposta |
| A47c-5 | Item segurado pode não estar no grafo no momento da ingestão (NFC-e processada DEPOIS do bilhete) | Aresta `assegura` é opcional; reprocessar via `./run.sh --religar` (Sprint 48) ou marcar TODO no nó Apolice |
| A20 (cross) | Glyphs corrompidos em PDF nativo | Usar `src/intake/glyph_tolerant.py` em todas as regex |

Referência: `docs/ARMADILHAS.md`

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `.venv/bin/pytest tests/test_cupom_garantia_estendida_pdf.py -v` passa com cobertura >= 80%
- [ ] 4 bilhetes de fixture processadas; 100% dos campos canônicos preenchidos em todas
- [ ] Grafo após processamento tem 1 nó `seguradora` (MAPFRE), N nós `apolice`, arestas `emitida_por` e `vendida_em` íntegras
- [ ] Quando rodado APÓS Sprint 44b ter processado o NFC-e da Americanas, aresta `assegura` aparece para 2 dos 4 bilhetes (os que casam Item por descrição+data+varejo)
- [ ] `mappings/seguradoras.yaml` tem MAPFRE registrada com CNPJ 61.074.175/0001-38, código SUSEP 06238

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_cupom_garantia_estendida_pdf.py -v
cp tests/fixtures/garantias_estendidas/*.pdf data/raw/andre/garantias_estendidas/
cp tests/fixtures/garantias_estendidas/*.png data/raw/andre/garantias_estendidas/
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='apolice';"
# esperado: == número de bilhetes únicos nas fixtures (4)
sqlite3 data/output/grafo.sqlite "SELECT n.nome_canonico FROM node n WHERE n.tipo='seguradora';"
# esperado: 'MAPFRE Seguros Gerais S.A.' ou variação canônica
```

## Conferência Artesanal Opus

**Arquivos originais a ler:**

- Cada PDF/imagem em `tests/fixtures/garantias_estendidas/` -- inspecionar visualmente
- Render visual via `pdfplumber.Page.to_image(resolution=120)` ou abrir PNG diretamente
- Output do grafo: `sqlite3 data/output/grafo.sqlite` queries acima

**Checklist:**

1. Para cada bilhete: número de bilhete extraído bate com o que está visível no PDF/imagem?
2. Vigência (início e fim) extraída no formato ISO; bate com as datas escritas em DD/MM/AAAA no documento?
3. Prêmio total = prêmio líquido + IOF? (validação numérica)
4. Bem segurado é frase coerente com o produto fotografado/mencionado na NFC-e pareada?
5. Seguradora resolvida pelo CNPJ; cadastro novo gerou proposta?
6. Bilhete em scan teve OCR razoável? Se algum campo crítico (número, SUSEP, CPF) ficou ilegível, o documento foi para `_classificar/_aguardando_revisao_humana/` em vez de propagar dado inventado?
7. Aresta `assegura` foi criada nos casos pareáveis?

**Relatório esperado em `docs/propostas/sprint_47c_conferencia.md`:**

- Tabela: bilhete | tipo (nativo/scan) | campos extraídos OK? | seguradora resolvida? | aresta assegura criada? | observação
- Variantes de glyph encontradas que precisam entrar em `src/intake/glyph_tolerant.py`
- Variantes de "Forma de Pagamento" que precisam entrar em normalizador
- Seguradoras novas detectadas que precisam entrar em `mappings/seguradoras.yaml`

**Critério de aprovação:** 4 bilhetes de fixtures (2 nativos + 2 scan) com 100% dos campos críticos (número, SUSEP, CPF, prêmio, vigência, seguradora_cnpj, bem_segurado) extraídos corretamente.

---

*"O seguro não evita o sinistro -- mas distribui o peso." -- princípio atuarial*
