## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 46
  title: "Extrator de XML NFe (máxima precisão)"
  touches:
    - path: src/extractors/xml_nfe.py
      reason: "parser XML NFe via xml.etree; extrai cabeçalho, emissor, destinatário, itens e tributação completos"
    - path: pyproject.toml
      reason: "eventual lxml para XPath mais rico (opcional, decisão interna)"
    - path: src/pipeline.py
      reason: "registra extrator"
  n_to_n_pairs: []
  forbidden:
    - src/extractors/danfe_pdf.py  # XML prefere sobre DANFE quando ambos existem
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_xml_nfe.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Extrator processa XML NFe padrão SEFAZ (layout 4.0) sem perda de dado"
    - "Chave 44 dígitos, CNPJ emissor, destinatário, todos itens com NCM/CFOP/qtd/valor/ICMS/IPI/PIS/COFINS persistidos no grafo"
    - "Quando NFe já foi extraída via DANFE (mesma chave), XML sobrescreve com dados mais ricos e marca origem_fonte=xml_nfe"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 46 -- Extrator de XML NFe

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** MEDIA
**Tipo:** Feature
**Dependências:** Sprint 41 (intake roteia XML), Sprint 42 (grafo), Sprint 44 (ingestor_documento compartilhado)
**Desbloqueia:** Precisão máxima em análise de IRPF e linking
**Issue:** --
**ADR:** ADR-14

---

## Como Executar

- `./run.sh --tudo`
- `.venv/bin/pytest tests/test_xml_nfe.py -v`

### O que NÃO fazer

- NÃO adicionar Pydantic/XSD validation pesada -- parse direto com stdlib
- NÃO ignorar namespaces (SEFAZ usa `http://www.portalfiscal.inf.br/nfe`)
- NÃO escrever o XML de volta após edição -- fonte imutável

---

## Problema

XML NFe é a fonte canônica: estruturado, com schema SEFAZ estável, contém tudo que o DANFE tem mais tributos detalhados. Quando disponível, deve ser preferido sobre DANFE PDF.

Usuários obtém XML:
- Portal do cliente (Receita, SAT, Bling)
- Anexo de e-mail da loja
- Integração de marketplaces (dentro de ZIP)

Parsing é bem mais simples que DANFE -- XPath direto. O desafio é só aguentar as variações de layout (4.0 é o atual, mas 3.10 ainda aparece em documentos antigos).

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Ingestor documento | `src/graph/ingestor_documento.py` (Sprint 44) | Persistência no grafo |
| Parser XML | `xml.etree.ElementTree` (stdlib) | Suficiente para NFe |

## Implementação

### Fase 1: parse de cabeçalho e itens

```python
NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

def extrair(caminho: Path) -> dict:
    tree = ET.parse(caminho)
    root = tree.getroot()
    infNFe = root.find(".//nfe:infNFe", NS)
    chave = infNFe.get("Id", "").replace("NFe", "")

    emit = infNFe.find("nfe:emit", NS)
    dest = infNFe.find("nfe:dest", NS)
    ide = infNFe.find("nfe:ide", NS)
    total = infNFe.find("nfe:total/nfe:ICMSTot", NS)

    cabecalho = {
        "chave": chave,
        "cnpj_emissor": emit.findtext("nfe:CNPJ", default="", namespaces=NS),
        "razao_emissor": emit.findtext("nfe:xNome", default="", namespaces=NS),
        "cnpj_destinatario": dest.findtext("nfe:CNPJ", default="", namespaces=NS)
                           or dest.findtext("nfe:CPF", default="", namespaces=NS),
        "data_emissao": ide.findtext("nfe:dhEmi", default="", namespaces=NS)[:10],
        "numero": ide.findtext("nfe:nNF", default="", namespaces=NS),
        "total": float(total.findtext("nfe:vNF", default="0", namespaces=NS)),
    }

    itens = []
    for det in infNFe.findall("nfe:det", NS):
        prod = det.find("nfe:prod", NS)
        imposto = det.find("nfe:imposto", NS)
        itens.append({
            "numero_item": det.get("nItem"),
            "codigo": prod.findtext("nfe:cProd", default="", namespaces=NS),
            "descricao": prod.findtext("nfe:xProd", default="", namespaces=NS),
            "ncm": prod.findtext("nfe:NCM", default="", namespaces=NS),
            "cfop": prod.findtext("nfe:CFOP", default="", namespaces=NS),
            "unidade": prod.findtext("nfe:uCom", default="", namespaces=NS),
            "qtd": float(prod.findtext("nfe:qCom", default="0", namespaces=NS)),
            "valor_unit": float(prod.findtext("nfe:vUnCom", default="0", namespaces=NS)),
            "valor_total": float(prod.findtext("nfe:vProd", default="0", namespaces=NS)),
            "icms_valor": _tributo_valor(imposto, "ICMS", "vICMS"),
            "ipi_valor": _tributo_valor(imposto, "IPI", "vIPI"),
            "pis_valor": _tributo_valor(imposto, "PIS", "vPIS"),
            "cofins_valor": _tributo_valor(imposto, "COFINS", "vCOFINS"),
        })

    return {"cabecalho": cabecalho, "itens": itens, "origem_fonte": "xml_nfe"}
```

### Fase 2: sobrescrita de DANFE existente

Se já existe node `documento` com mesma `nome_canonico` (chave 44) originado de DANFE:
- Atualiza metadata com dados do XML
- Adiciona `metadata.origem_fonte = "xml_nfe"` (prioridade)
- Remove nodes `item` antigos e recria (dados XML são mais completos)

### Fase 3: testes

Fixture `tests/fixtures/nfe/nfe_sample.xml` (XML anonimizado padrão 4.0).

- `test_extrai_chave_emissor_destinatario`
- `test_extrai_todos_itens_com_tributos`
- `test_xml_sobrescreve_danfe_existente`
- `test_xml_com_namespace_errado_erro_claro`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A46-1 | Atributo `Id="NFe<chave>"` vs `Id="<chave>"` | Regex `replace("NFe", "")` antes de usar |
| A46-2 | NFe cancelada tem protocolo de cancelamento no mesmo XML | Checar `<nfeProc><protNFe><infProt><cStat>101</cStat>` para cancelamento |
| A46-3 | Layout 3.10 tem tags ligeiramente diferentes | Fallback: se layout 4.0 não casa, tenta 3.10 ou avisa |
| A46-4 | XML dentro de ZIP com encoding diferente quebra parser | `ET.parse` aceita arquivo com encoding declarado; se der erro, ler bytes e passar pra `ET.fromstring` |
| A46-5 | Destinatário pode ser PF (CPF) ou PJ (CNPJ) | Tentar CNPJ primeiro, fallback CPF |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] Parser extrai 1 XML NFe layout 4.0 sem perda
- [ ] Testes passam
- [ ] XML sobrescreve DANFE PDF no grafo quando aplicável
- [ ] Grafo tem metadata `origem_fonte=xml_nfe` nos nodes criados

## Verificação end-to-end

```bash
cp tests/fixtures/nfe/nfe_sample.xml data/raw/andre/nfs_fiscais/xml/
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "SELECT JSON_EXTRACT(metadata, '\$.origem_fonte'), COUNT(*) FROM node WHERE tipo='item' GROUP BY 1;"
# esperado: xml_nfe > 0
.venv/bin/pytest tests/test_xml_nfe.py -v
```

## Conferência Artesanal Opus

**Arquivos originais a ler:**

- Cada `.xml` em `data/raw/andre/nfs_fiscais/xml/` (abrir e ler visualmente)
- Query SQL dos items extraídos

**Checklist:**

1. Todos os `<det>` do XML viraram um `item` no grafo?
2. Valores dos tributos (ICMS, IPI, PIS, COFINS) estão nos metadados do item?
3. Quando havia DANFE PDF da mesma chave, houve sobrescrita?
4. Destinatário bate com o usuário (CPF/CNPJ esperado)?

**Relatório esperado em `docs/propostas/sprint_46_conferencia.md`**: tabela de XMLs processados com deltas vs DANFE PDF.

**Critério de aprovação**: 100% dos itens do XML estão no grafo com tributos; nenhum DANFE "corrompeu" dado de XML mais recente.

---

*"O ideal do dado é a estrutura -- o XML é a forma do imposto." -- princípio do auditor*
