## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 47b
  title: "Extrator de Documento de Garantia (foto/PDF/email)"
  touches:
    - path: src/extractors/garantia.py
      reason: "parser permissivo para termos de garantia: produto, serie, prazo, fornecedor, condicoes"
    - path: mappings/garantia_padroes.yaml
      reason: "padrões de fornecedores conhecidos (Americanas, Magalu, Amazon) com layouts"
    - path: src/pipeline.py
      reason: "registra extrator"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_garantia.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Extrai produto, número de série, data de início, prazo em meses e fornecedor"
    - "Grafo: node Garantia + aresta cobre apontando para item (quando linking existir)"
    - "Alerta automático quando faltam 30 dias para fim da garantia"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 47b -- Extrator de Documento de Garantia

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** BAIXA
**Tipo:** Feature
**Dependências:** Sprint 41, 42, 44 (ingestor), 45 (OCR)
**Desbloqueia:** Alerta proativo antes de fim de garantia
**Issue:** --
**ADR:** ADR-14

---

## Como Executar

- `./run.sh --tudo`
- `.venv/bin/pytest tests/test_garantia.py`

### O que NÃO fazer

- NÃO acionar e-mail automatizado com alerta (apenas registrar no log)
- NÃO confiar em OCR de termo genérico com texto longo -- focar em campos essenciais

---

## Problema

Garantias estendidas (extensão de 12 ou 24 meses) que vêm como:
- Termo PDF anexo de e-mail
- Foto do comprovante impresso entregue no PDV
- E-mail automático com dados do registro

Hoje ficam em arquivo solto no celular ou Drive. Sem rastreamento, perdemos o direito de acionar a garantia no prazo.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| OCR comum | `src/extractors/_ocr_comum.py` | Normalização e OCR |
| Ingestor documento | `src/graph/ingestor_documento.py` | Persistência |
| Grafo extensível | Node `garantia` previsto em ADR-14 |

## Implementação

### Fase 1: parser

`_parse_garantia(texto: str) -> dict`:

Regex essenciais:
- Produto: "PRODUTO:" ou primeira linha alfabética sem código
- Número de série: "S/N:", "SERIAL:", "IMEI:", "NOTA FISCAL:"
- Data de início: "DATA DE COMPRA:", "EMISSÃO:"
- Prazo: "PRAZO DE GARANTIA:" (pegar dígitos + "MESES" ou "ANOS")
- Fornecedor: CNPJ emissor ou nome

### Fase 2: grafo

- Node `garantia` (nome_canonico = número de série ou hash do conteúdo)
- Metadata: `{produto, data_inicio, data_fim, prazo_meses, fornecedor_cnpj, condicoes}`
- Aresta `fornecido_por` → fornecedor
- Aresta `cobre` → item (criada quando linking Sprint 48 identifica qual item da NF é o produto)

### Fase 3: alerta de vencimento

Nova query em `src/graph/queries.py`:

```python
def garantias_proximas_do_vencimento(dias: int = 30) -> list[dict]:
    # SELECT * FROM node WHERE tipo='garantia' AND
    #   JULIANDAY(metadata->>'data_fim') - JULIANDAY('now') BETWEEN 0 AND :dias
    ...
```

Dashboard Sprint 51 exibe; pipeline loga warnings.

### Fase 4: testes

Fixtures em `tests/fixtures/garantias/`:
- `garantia_americanas_12m.pdf`
- `garantia_magalu_24m.pdf`
- `garantia_email.eml`

Testes:
- `test_extrai_prazo_24_meses`
- `test_calcula_data_fim_corretamente`
- `test_email_garantia_extrai_anexo`
- `test_alerta_30_dias_antes_fim`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A47b-1 | "Prazo de Garantia: 12 (doze) meses" vs "12 meses" | Regex extrai só o número |
| A47b-2 | Garantia estendida vs garantia legal (90 dias) -- metadados distintos | Campo `tipo_garantia` no metadata |
| A47b-3 | E-mail de garantia tem HTML denso com template | Usar `email.message.walk()` e pegar parte text/plain ou fallback bs4 |
| A47b-4 | Garantia de serviço (instalação, suporte) sem produto físico | Campo `produto` pode ser vazio; dispensa linking |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] 3 fixtures processadas com produto/serie/prazo
- [ ] Grafo tem nodes `garantia`
- [ ] Log contém `garantias_proximas_do_vencimento` quando aplicável

## Verificação end-to-end

```bash
cp tests/fixtures/garantias/*.* data/raw/andre/garantias/
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "SELECT nome_canonico, JSON_EXTRACT(metadata, '\$.data_fim') FROM node WHERE tipo='garantia';"
```

## Conferência Artesanal Opus

**Arquivos originais a ler:** cada termo em `data/raw/andre/garantias/`.

**Checklist:**

1. Prazo extraído bate com o documento?
2. Número de série é o mesmo do item comprado (quando rastreável)?
3. Data fim está calculada corretamente (data início + prazo)?
4. Aresta `cobre` liga à NF de compra se existir?

**Relatório em `docs/propostas/sprint_47b_conferencia.md`**: fornecedores novos que precisam entrar em `mappings/garantia_padroes.yaml`.

**Critério**: 3 garantias diferentes com todos os campos essenciais extraídos.

---

*"O que vale comprar vale lembrar." -- princípio do consumidor cauteloso*
