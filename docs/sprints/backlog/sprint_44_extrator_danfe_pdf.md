## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 44
  title: "Extrator de DANFE PDF (NFe formal)"
  touches:
    - path: src/extractors/danfe_pdf.py
      reason: "extrai cabeçalho (CNPJ emissor, chave 44 dígitos, data emissão, total) e itens (descrição, NCM, qtd, valor unit, ICMS/IPI/PIS) de DANFE PDF"
    - path: src/graph/ingestor_documento.py
      reason: "função shared: insere Documento + Itens + Fornecedor + arestas no grafo -- reusada por 45/46/47"
    - path: mappings/layouts_danfe.yaml
      reason: "registra variações conhecidas de layout DANFE para regex especializada"
    - path: src/pipeline.py
      reason: "registra DanfePDF em _descobrir_extratores"
  n_to_n_pairs:
    - [src/extractors/danfe_pdf.py, src/graph/ingestor_documento.py]
  forbidden:
    - src/extractors/energia_ocr.py
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_danfe_pdf.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Extrai >= 3 DANFEs de fornecedores diferentes com >= 95% dos itens recuperados"
    - "Chave 44 dígitos validada (dígito verificador correto)"
    - "CNPJ emissor batendo com chave"
    - "Grafo recebe 1 Documento + N Itens + 1 Fornecedor + arestas corretas"
    - "Layout desconhecido não crash -- vai pra fallback supervisor"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 44 -- Extrator de DANFE PDF

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprint 41 (intake roteia DANFE para pasta correta), Sprint 42 (grafo recebe nodes)
**Desbloqueia:** Sprint 48 (linking), Sprint 51 (dashboard mostra NFs)
**Issue:** --
**ADR:** ADR-14 (grafo extensível)

---

## Como Executar

- `.venv/bin/pytest tests/test_danfe_pdf.py -v`
- `./run.sh --tudo` (extrator roda no pipeline e popula grafo)

### O que NÃO fazer

- NÃO extrair tributos complexos (só o essencial: ICMS, IPI, PIS, COFINS quando fáceis)
- NÃO normalizar NCM para tabela completa -- só captura o código
- NÃO tentar DANFE de NFCe (é outro formato, fica para sprint futura)

---

## Problema

DANFE é a representação impressa da NFe. O PDF contém cabeçalho estruturado e uma tabela de produtos. Formatos variam por layout de emissor (Bling, eNotas, NFe.io, SEFAZ estadual), mas o núcleo é consistente:

- Chave de acesso (44 dígitos) no topo/código de barras
- CNPJ emissor, razão social, endereço
- Destinatário (CPF/CNPJ)
- Data de emissão, número, série
- Itens em tabela: NCM, descrição, CFOP, Un, Qtd, V. Unit, V. Total
- Totais: produtos, ICMS, IPI, desconto, total NF

A extração hoje não existe -- o pipeline pega só o débito bancário ligado à NF.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| ExtratorBase | `src/extractors/base.py` | Classe base + dataclass `Transacao` (não se encaixa 1:1, usar interface nova) |
| pdfplumber | lib | Extração de texto e tabelas de PDF |
| Grafo | `src/graph/db.py` | Persistência de Documento + Item |
| Deteção de CNPJ | `src/transform/irpf_tagger.py:_REGEX_CNPJ` | Reusar regex |

## Implementação

### Fase 1: parser do cabeçalho

`_parse_cabecalho(texto: str) -> dict`:
- chave 44 dígitos via `re.compile(r"\d{4}\s*\d{4}(?:\s*\d{4}){9}")`
- CNPJ emissor via `_REGEX_CNPJ`
- Data emissão: várias regex por layout; fallback: primeira data DD/MM/YYYY
- Número NF: `Nº\s*(\d+)`
- Total NF: linha "VALOR TOTAL DA NOTA" seguida de moeda

Validação: dígitos verificadores da chave 44 via algoritmo padrão SEFAZ.

### Fase 2: parser da tabela de itens

`_parse_itens(pagina: pdfplumber.Page) -> list[dict]`:

Usa `page.extract_tables()` quando layout é tabela bem-comportada. Fallback: regex por linha quando tabela não parseia.

Campos por item:
- `descricao`: primeira coluna relevante
- `ncm`: regex `\b\d{8}\b` próximo da descrição
- `cfop`: regex `\b5\d{3}\b`
- `unidade`: UN, KG, etc
- `quantidade`: float
- `valor_unit`: float
- `valor_total`: float
- `icms_valor`, `ipi_valor`: opcionais; se fáceis de extrair, ok

### Fase 3: ingestão no grafo

`src/graph/ingestor_documento.py`:

```python
def ingerir_documento(
    db: GrafoDB,
    tipo_documento: str,       # "danfe_nfe"
    caminho_arquivo: Path,
    cabecalho: dict,
    itens: list[dict],
) -> int:
    doc_id = db.upsert_node("documento", cabecalho["chave"], metadata={...}, aliases=[])
    fornecedor_id = db.upsert_node("fornecedor", cabecalho["cnpj_emissor"], metadata={...})
    db.adicionar_edge(doc_id, fornecedor_id, "fornecido_por", evidencia={"cnpj_extraido": ...})
    periodo_id = db.upsert_node("periodo", cabecalho["mes_ref"])
    db.adicionar_edge(doc_id, periodo_id, "ocorre_em")
    for idx, item in enumerate(itens):
        item_id = db.upsert_node("item", item["descricao"], metadata={**item, "documento_id": doc_id})
        db.adicionar_edge(doc_id, item_id, "contem_item", evidencia={"ordem_linha": idx})
    return doc_id
```

Retornado para uso em Sprint 48 (linking a transação).

### Fase 4: registro no pipeline

Em `src/pipeline.py:_descobrir_extratores`:

```python
try:
    from src.extractors.danfe_pdf import ExtratorDanfePDF
    extratores.append(ExtratorDanfePDF)
except ImportError as e:
    logger.warning("Extrator danfe_pdf indisponível: %s", e)
```

### Fase 5: testes

Fixtures em `tests/fixtures/danfes/` (3 PDFs sintéticos ou anonimizados):
- `danfe_americanas.pdf` (varejo com 5+ itens)
- `danfe_servico_ti.pdf` (serviço, 1 item)
- `danfe_mercado.pdf` (supermercado, 20+ itens, layout denso)

Testes:
- `test_extrai_chave_44_digitos`
- `test_valida_digito_verificador_chave`
- `test_extrai_5_itens_corretamente`
- `test_item_sem_ncm_nao_crasha`
- `test_layout_desconhecido_retorna_fallback`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A44-1 | `extract_tables()` do pdfplumber falha em PDFs com tabela sem bordas | Fallback regex linha a linha quando retorno vem vazio |
| A44-2 | Chave 44 dígitos as vezes é quebrada em múltiplas linhas | Normalizar espaços/quebras antes da regex |
| A44-3 | CFOP 5XXX é saída; 1XXX/2XXX é entrada -- extrator assume saída (PDF emitido) | Documentar no header do módulo |
| A44-4 | DANFE com múltiplas páginas: itens continuam nas seguintes | Iterar por `pdf.pages` e concatenar |
| A44-5 | Valores em R$ com ponto de milhar "1.234,56" | Usar o `_parse_valor_br` já existente em `contracheque_pdf.py` |
| A44-6 | NFe cancelada ainda tem DANFE -- pipeline processaria dado inválido | Detectar "NFe CANCELADA" no rodapé e marcar com flag; não linkar a transação |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] `.venv/bin/pytest tests/test_danfe_pdf.py -v` passa
- [ ] 3 DANFEs de fixture processadas sem warnings
- [ ] Grafo após processamento tem nodes Documento + Fornecedor + Items
- [ ] Recall de itens >= 95% em amostra validada pelo supervisor

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_danfe_pdf.py -v
cp tests/fixtures/danfes/*.pdf data/raw/andre/nfs_fiscais/
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='item';"
# esperado: >= número de itens nas fixtures somados
```

## Conferência Artesanal Opus

**Arquivos originais a ler:**

- Cada DANFE PDF em `data/raw/andre/nfs_fiscais/*.pdf`
- Output do grafo: `sqlite3 data/output/grafo.sqlite "SELECT n.nome_canonico, n.metadata FROM node n WHERE n.tipo='item' AND JSON_EXTRACT(n.metadata, '$.documento_id')=<doc_id>;"`

**Checklist:**

1. Para cada DANFE lida: o número de itens no PDF bate com o número de nodes `item` no grafo?
2. Valores (qtd × unit = total) batem com o PDF linha a linha?
3. CNPJ emissor extraído casa com o campo "Razão Social" do PDF?
4. Chave 44 dígitos validou no dígito verificador?
5. NCM extraído é plausível (8 dígitos, produto coerente)?

**Relatório esperado em `docs/propostas/sprint_44_conferencia.md`**:

- Tabela: DANFE → nº itens PDF → nº itens grafo → recall → observação
- Layouts novos encontrados que precisam entrar em `mappings/layouts_danfe.yaml`
- Propostas de ajuste regex

**Critério de aprovação**: 3 DANFEs de fornecedores distintos com recall >= 95% cada.

---

*"A nota fiscal conta a história que o banco não conta." -- princípio do contador*
