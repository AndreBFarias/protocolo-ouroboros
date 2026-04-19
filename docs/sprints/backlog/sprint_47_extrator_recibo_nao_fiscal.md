## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 47
  title: "Extrator de Recibo Não-Fiscal (foto / PDF livre)"
  touches:
    - path: src/extractors/recibo_nao_fiscal.py
      reason: "parser permissivo para comprovantes sem CNPJ (Pix impresso, recibo manuscrito, voucher)"
    - path: mappings/layouts_recibo.yaml
      reason: "padrões conhecidos (Pix Banco X, Pix Banco Y, voucher iFood, voucher 99)"
    - path: src/pipeline.py
      reason: "registra extrator com prioridade baixa (catch-all depois de outros)"
  n_to_n_pairs:
    - [mappings/layouts_recibo.yaml, src/extractors/recibo_nao_fiscal.py]
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_recibo_nao_fiscal.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Extrai valor, data, contraparte de comprovante de Pix impresso"
    - "Voucher de serviço (iFood, 99) identificado pelo layout e valor extraído"
    - "Sem itens individuais estruturados (aceitável: 1 item único com descrição do serviço)"
    - "Confidence < 60% manda para supervisor"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 47 -- Extrator de Recibo Não-Fiscal

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** MEDIA
**Tipo:** Feature
**Dependências:** Sprint 41, 42, 45 (reusa _ocr_comum.py)
**Desbloqueia:** Linking de transferências Pix via comprovante
**Issue:** --
**ADR:** ADR-14

---

## Como Executar

- `./run.sh --tudo`
- `.venv/bin/pytest tests/test_recibo_nao_fiscal.py -v`

### O que NÃO fazer

- NÃO tentar extrair itens individuais -- recibo não tem estrutura tabular
- NÃO adivinhar CNPJ quando não estiver presente
- NÃO duplicar lógica de OCR -- reusar `src/extractors/_ocr_comum.py`

---

## Problema

Muitas despesas não têm NF: comprovante de Pix enviado ao entregador, recibo de aluguel manuscrito, voucher de serviço (iFood, 99, Uber com desconto). Esses documentos trazem contexto importante: valor, data, contraparte, descrição do serviço.

Sem extrator, o pipeline guarda só a transação bancária -- perde o "pagamento a quem" e "por quê".

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| OCR comum | `src/extractors/_ocr_comum.py` (Sprint 45) | Preview e normalização |
| Ingestor documento | `src/graph/ingestor_documento.py` | Persistência |

## Implementação

### Fase 1: detecção de layout

`mappings/layouts_recibo.yaml`:

```yaml
layouts:
  - id: pix_nubank
    identificadores: ["Nubank", "Pix enviado", "Pix recebido"]
    regex_valor: "R\\$\\s*([\\d.]+,\\d{2})"
    regex_data: "(\\d{2}/\\d{2}/\\d{4}|\\d{2} de \\w+ de \\d{4})"
    regex_contraparte: "(?:Para|De)\\s+(.+?)\\s+(?:CPF|CNPJ|\\d)"

  - id: pix_itau
    identificadores: ["Itaú", "Comprovante de Pix"]
    # ...

  - id: voucher_ifood
    identificadores: ["iFood", "Pedido #"]
    regex_valor: "(?:Total|Valor)\\s+R\\$\\s*([\\d.]+,\\d{2})"
    regex_descricao: "Pedido\\s+#(\\d+)"
```

### Fase 2: extrator

```python
def extrair(caminho: Path) -> dict:
    texto = _obter_texto(caminho)
    layout = _detectar_layout(texto)
    if not layout:
        return {"tipo_documento": "recibo_desconhecido", "confianca": 0.0, "texto_cru": texto}

    dados = _aplicar_layout(layout, texto)
    return {
        "tipo_documento": "recibo_nao_fiscal",
        "layout": layout["id"],
        "valor": dados["valor"],
        "data": dados["data"],
        "contraparte": dados.get("contraparte"),
        "descricao": dados.get("descricao"),
        "confianca": dados["confianca"],
    }

def _obter_texto(caminho: Path) -> str:
    if caminho.suffix.lower() == ".pdf":
        import pdfplumber
        with pdfplumber.open(caminho) as pdf:
            return pdf.pages[0].extract_text() or ""
    from src.extractors._ocr_comum import carregar_imagem_normalizada, ocr_com_confidence
    img = carregar_imagem_normalizada(caminho)
    texto, _ = ocr_com_confidence(img)
    return texto
```

### Fase 3: persistência no grafo

Cria nodes:
- `documento` (tipo=recibo_nao_fiscal, metadata={valor, data, contraparte, layout})
- Se contraparte tem CPF/CNPJ detectado, cria `fornecedor` e `fornecido_por`
- Senão, cria `fornecedor` com `nome_canonico=contraparte` e aresta com `confianca=0.5`
- Sem `item` (recibo não é granular)

### Fase 4: testes

Fixtures: 3 comprovantes anonimizados (Pix Nubank, Pix Itaú, voucher iFood).

Testes:
- `test_pix_nubank_extrai_valor_data_contraparte`
- `test_voucher_ifood_extrai_pedido`
- `test_layout_desconhecido_retorna_confianca_zero`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A47-1 | CPF mascarado (`***.123.***-**`) não é CPF válido | Capturar como string literal; não tentar validar |
| A47-2 | "Pix recebido" vs "Pix enviado" muda o sinal da transação | Layout precisa mapear qual caso gera despesa ou receita (ou nenhum, só metadata) |
| A47-3 | Voucher com desconto tem 2 valores (bruto e líquido); confusão | Capturar ambos em metadata; registrar valor líquido como "valor" |
| A47-4 | Foto de tela (screenshot) vs foto de papel impresso têm qualidades diferentes | Screenshot sempre tem texto preciso; papel exige OCR tolerante |
| A47-5 | Caracteres especiais no nome da contraparte (ã, ç) falham em OCR ruim | Aplicar `unicodedata.normalize("NFKC", ...)` pós-OCR |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] 3 layouts cobertos com fixtures
- [ ] Testes passam
- [ ] Grafo recebe nodes de documento + fornecedor
- [ ] Confianca baixa manda para `docs/propostas/extracao_recibo/`

## Verificação end-to-end

```bash
cp tests/fixtures/recibos/*.jpg tests/fixtures/recibos/*.pdf data/raw/andre/recibos/
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='documento' AND JSON_EXTRACT(metadata, '\$.tipo_documento')='recibo_nao_fiscal';"
.venv/bin/pytest tests/test_recibo_nao_fiscal.py -v
```

## Conferência Artesanal Opus

**Arquivos originais a ler:** cada comprovante em `data/raw/andre/recibos/` (visual + metadata extraída).

**Checklist:**

1. Valor extraído bate com o visual do comprovante?
2. Data e contraparte estão corretas?
3. Layout aplicado foi o correto (Pix Nubank vs Itaú, etc)?

**Relatório em `docs/propostas/sprint_47_conferencia.md`**: layouts novos encontrados que precisam entrar em `mappings/layouts_recibo.yaml`.

**Critério**: 3 comprovantes de fontes diferentes com valor+data+contraparte corretos.

---

*"A memória do recibo é maior que a do banco." -- princípio do registrador*
