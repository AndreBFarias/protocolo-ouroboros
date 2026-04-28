## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 107
  title: "Fornecedor sintetico para impostos (DAS PARCSN, DARF, etc.) -- Receita Federal em vez de razao_social do contribuinte"
  prioridade: P2
  estimativa: ~1.5h
  origem: "achado da fase Opus Sprint 103: 13 parcelas DAS PARCSN tem razao_social='ANDRE DA SILVA BATISTA DE FARIAS' como 'fornecedor', mas semanticamente o fornecedor e a Receita Federal"
  touches:
    - path: mappings/fornecedores_sinteticos.yaml
      reason: "novo: declara entidades fiscais canonicas (RECEITA_FEDERAL, INSS, FGTS, ICMS, etc.) com CNPJ oficial"
    - path: src/extractors/das_parcsn_pdf.py
      reason: "ao ingerir, usar fornecedor RECEITA_FEDERAL em vez do contribuinte"
    - path: src/extractors/dirpf_dec.py
      reason: "idem para DIRPF"
    - path: src/graph/ingestor_documento.py
      reason: "logica generica: se tipo_documento esta em mappings/fornecedores_sinteticos.yaml, usar fornecedor mapeado"
    - path: tests/test_fornecedor_sintetico_impostos.py
      reason: "regressao: DAS PARCSN gera node fornecedor=RECEITA_FEDERAL, nao Andre"
  forbidden:
    - "Quebrar nodes ja existentes no grafo (migracao via Sprint 104 --reextrair-tudo)"
    - "Mudar razao_social que e contribuinte (preservar em metadata.contribuinte para auditoria)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_fornecedor_sintetico_impostos.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "mappings/fornecedores_sinteticos.yaml declara RECEITA_FEDERAL com CNPJ 00.394.460/0001-41 e razao_social oficial"
    - "Documentos tipo das_parcsn_*, darf, dirpf_retif sao ingeridos com fornecedor=RECEITA_FEDERAL no grafo"
    - "Campo metadata.contribuinte preserva o nome do contribuinte original para auditoria"
    - "Linker (Sprint 95+) aceita CNPJ da Receita Federal na contraparte de tx 'PIX RECEITA FEDERAL' (cnpj_bate=True)"
    - "Documentos antigos sao migrados pela proxima rodada de --reextrair-tudo (Sprint 104) -- nao por esta sprint"
  proof_of_work_esperado: |
    .venv/bin/python -c "
    from src.graph.db import GrafoDB
    db = GrafoDB('data/output/grafo.sqlite')
    cur = db._conn.execute('''
      SELECT COUNT(*) FROM node n1
      JOIN edge e ON e.src_id=n1.id AND e.tipo='fornecido_por'
      JOIN node n2 ON n2.id=e.dst_id
      WHERE n1.tipo='documento' 
        AND json_extract(n1.metadata, '$.tipo_documento') LIKE 'das_parcsn_%'
        AND n2.nome_canonico='RECEITA_FEDERAL'
    ''')
    print(f'DAS PARCSN apontando para Receita Federal: {cur.fetchone()[0]}')
    "
    # Antes (apos Sprint 107 codada mas pre-reextracao): 0
    # Depois de --reextrair-tudo: ~13 (parcelas existentes)
```

---

# Sprint 107 -- Fornecedor sintetico impostos

**Status:** BACKLOG (P2, criada 2026-04-28 como achado Opus Sprint 103)

## Motivação

Fase Opus identificou que TODAS as 13 parcelas DAS PARCSN no grafo tem `metadata.razao_social = "ANDRE DA SILVA BATISTA DE FARIAS"` -- que e o **contribuinte**, não o **fornecedor** semântico. O recebedor real do PIX e a **Receita Federal** (CNPJ 00.394.460/0001-41).

Consequencias:
- Linker (Sprint 95) não consegue casar `cnpj_bate=True` entre o documento e a tx PIX.
- Aba Pagamentos / categorias agrupa parcelas DAS sob "Andre" como fornecedor (errado).
- Relatórios IRPF não distinguem natureza (imposto vs receita propria).

## Implementação

### 1. `mappings/fornecedores_sinteticos.yaml`

```yaml
# Entidades fiscais com CNPJ oficial. Documentos cujo tipo casa com
# uma das chaves abaixo terao 'fornecido_por' apontando para o sintetico,
# mantendo o contribuinte em metadata.contribuinte para auditoria.

fornecedores:
  RECEITA_FEDERAL:
    cnpj: "00394460000141"
    razao_social: "Receita Federal do Brasil"
    aliases: ["Receita Federal", "RFB", "PIX RECEITA FEDERAL"]
    aplica_a_tipos:
      - das_parcsn_andre
      - das_parcsn_vitoria
      - darf
      - dirpf_retif
      - irpf_parcela

  INSS:
    cnpj: "29979036000140"
    razao_social: "Instituto Nacional do Seguro Social"
    aliases: ["INSS", "Previdencia Social"]
    aplica_a_tipos:
      - guia_inss

  CEB:  # placeholder concreto / customizavel
    cnpj: "07522669000196"
    razao_social: "CEB Distribuicao S.A."
    aliases: ["CEB", "Neoenergia DF"]
    aplica_a_tipos:
      - conta_energia
```

### 2. Logica em `src/graph/ingestor_documento.py`

Função helper `_resolver_fornecedor_sintetico(tipo_documento) -> dict | None`:
- Carrega `fornecedores_sinteticos.yaml` (cache em modulo).
- Se tipo casa com `aplica_a_tipos`, retorna o dict do fornecedor sintetico.
- Caller usa `cnpj_emitente = sintetico["cnpj"]` em vez do contribuinte.

Em `ingerir_documento_fiscal`:
```python
sintetico = _resolver_fornecedor_sintetico(documento.get("tipo_documento"))
if sintetico:
    documento["metadata"]["contribuinte"] = documento.get("razao_social")  # auditoria
    documento["cnpj_emitente"] = sintetico["cnpj"]
    documento["razao_social"] = sintetico["razao_social"]
```

### 3. Migration via Sprint 104

Sprint 104 (--forcar-reextracao) limpa nodes documento e re-ingere. Apos esta sprint codada, rodar `./run.sh --reextrair-tudo` para que os 13 DAS PARCSN existentes ganhem o fornecedor correto.

## Testes regressivos

1. DAS PARCSN ingerido sintetico: node `documento` aponta para fornecedor RECEITA_FEDERAL via `fornecido_por`.
2. NFCe (tipo não-fiscal) preserva fornecedor real (Americanas, etc.).
3. Idempotencia: rodar 2x não duplica.
4. Backward-compat: docs sem `tipo_documento` no metadata caem no fluxo antigo (preserva razao_social).

## Dependências

- Sprint 47c (commit `XX`) ja tem helpers de upsert_fornecedor.
- Sprint 104 (commit `a7ed9e5`) e pre-requisito para migrar nodes existentes apos a fix.
- ADR-14 (tipos canonicos do grafo) precisa estender com nota sobre fornecedor sintetico (atualizar pos-sprint).
