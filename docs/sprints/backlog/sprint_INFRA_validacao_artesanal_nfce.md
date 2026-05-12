---
id: INFRA-VALIDACAO-ARTESANAL-NFCE
titulo: Validacao artesanal NFCe PDF -- 2 amostras lidas por Opus multimodal versus ETL com foco em drill-down item (P55 vs PS5)
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: [INFRA-OPUS-SCHEMA-EXTENDIDO]
esforco_estimado_horas: 2
origem: Plano 2026-05-12 secao Fase A1 -- NFCe so 2 nodes no grafo (drill-down item bloqueado); item "PEPSI 2L"/"PS5" provou que ETL local tem erro silencioso ("CONTROLE P55" registrado vs "PS5" canonico).  <!-- noqa: accent -->
mockup: novo-mockup/mockups/10-validacao-arquivos.html  <!-- noqa: accent -->
---

# Sprint INFRA-VALIDACAO-ARTESANAL-NFCE -- prova de paridade em NFCe PDF com foco em itens

## Contexto

Apenas 2 nodes `documento` com `tipo_documento='nfce_modelo_65'` existem no grafo (`data/output/grafo.sqlite`) — universo crítico baixo, mas o gap real está em **drill-down item**: das 41 entradas `item` no grafo, 1 mostrou erro fundamental — "CONTROLE P55" gravado em vez de "PS5" (PlayStation 5). O sistema reconhece a incerteza (campo `aliases` tem ambas variantes), mas o canônico ficou errado. Achado: `docs/auditorias/VALIDACAO_END2END_2026-05-08.md` caso 3.

NFCe modelo 65 (consumidor final) é a fonte rica de itens com EAN — vínculo produto canônico fundamental para análises tipo "quanto economizo trocando marca de chocolate?".

## Objetivo

1. Selecionar 2 NFCe reais (idealmente: a que teve P55→PS5 + outra de outro estabelecimento).
2. Para cada uma:
   - Capturar dict ETL via `from src.extractors.nfce_pdf import extrair`.
   - Capturar dict Opus via Read multimodal.
   - Persistir cache no schema canônico estendido (com `chave_44`).
   - Validar contra XML correlato (se houver — `data/raw/<...>/*.xml` com mesma chave).
   - Diff campo-a-campo + item-a-item.
3. Confirmar/refutar empíricamente o erro P55→PS5: pegar a NFCe específica e confrontar.
4. Relatório `docs/auditorias/VALIDACAO_ARTESANAL_NFCE_2026-MM-DD.md`.

## Validação ANTES (grep -- padrão (k))

```bash
ls data/raw/casal/nfs_fiscais/nfce/ 2>/dev/null || find data/raw -name "*nfce*" -type f | head
sqlite3 data/output/grafo.sqlite "SELECT id, json_extract(metadata,'\$.chave_44'), json_extract(metadata,'\$.emitente') FROM node WHERE tipo='documento' AND json_extract(metadata,'\$.tipo_documento')='nfce_modelo_65'"
sqlite3 data/output/grafo.sqlite "SELECT nome_canonico, aliases FROM node WHERE tipo='item' AND nome_canonico LIKE '%P55%' OR nome_canonico LIKE '%PS5%'"
.venv/bin/python -c "from src.extractors.nfce_pdf import extrair; print('importa OK')"
```

Confirma: (a) NFCe existem fisicamente em `data/raw/`, (b) grafo tem 2 nodes NFCe + arestas para itens, (c) item P55/PS5 está catalogado para confrontar, (d) extrator importa.

## Não-objetivos (padrão (t))

- **NÃO** validar mais de 2 amostras.
- **NÃO** corrigir item P55→PS5 nesta sprint — sprint-filha cuida da renomeação canônica.
- **NÃO** mexer em `aliases` do grafo manualmente (sem ferramenta canônica para isso ainda).
- **NÃO** baixar XML adicional da Receita; usar só XMLs já presentes no repo.
- **NÃO** persistir EAN inválido (treze dígitos numéricos é o contrato).

## Spec de implementação

Loop canônico de 7 passos. Diferenças específicas:

### Diferença 1 — Schema estendido (nfce_modelo_65)

```python
dict_opus_nfce = {
    "sha256": "...",
    "tipo_documento": "nfce_modelo_65",
    "chave_44": "<44 digitos>",
    "estabelecimento": {"razao_social": "...", "cnpj": "..."},
    "data_emissao": "YYYY-MM-DDTHH:MM:SS",
    "protocolo_autorizacao": "...",
    "xml_correlato_sha256": "..." or None,
    "itens": [
        {"codigo": "...", "ean": "<13 dig ou null>", "descricao": "...", "qtd": ..., "unidade": "...", "valor_unit": ..., "valor_total": ...},
        ...
    ],
    "total": ...,
    "forma_pagamento": "...",
    "extraido_via": "opus_v4_7_artesanal",
    "confianca_global": ...,
    "ts_extraido": "..."
}
```

### Diferença 2 — Cross-check XML

NFCe modelo 65 frequentemente vem com XML correlato. Se `data/raw/<...>*.xml` existe com mesma `chave_44`:

```python
import lxml.etree as ET
xml_tree = ET.parse("data/raw/.../NFCe.xml")
ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
total_xml = float(xml_tree.find(".//nfe:vNF", ns).text)
assert abs(dict_opus_nfce["total"] - total_xml) < 0.01, "Opus vs XML divergem!"
```

XML é fonte de verdade externa — bater contra ele dá uma terceira testemunha (defesa em camadas, padrão `(n)`).

### Diferença 3 — Item-a-item

Cada item da `dict_opus_nfce["itens"]` deve ser confrontado com `dict_etl["itens"]` por código (interno do estabelecimento) ou EAN:

```python
def comparar_itens(etl_itens, opus_itens):
    erros = []
    if len(etl_itens) != len(opus_itens):
        erros.append(("A", f"qtd_itens", len(etl_itens), len(opus_itens)))
    for opus_item in opus_itens:
        match = next((e for e in etl_itens if e.codigo == opus_item["codigo"] or e.ean == opus_item["ean"]), None)
        if match is None:
            erros.append(("A", f"item_ausente_etl", opus_item["codigo"], None))
            continue
        if match.descricao != opus_item["descricao"]:
            erros.append(("B", f"descricao", match.descricao, opus_item["descricao"]))
        if abs(match.valor_total - opus_item["valor_total"]) > 0.01:
            erros.append(("A", f"valor_total_item", match.valor_total, opus_item["valor_total"]))
    return erros
```

### Diferença 4 — Confirmação P55/PS5

Pegar a NFCe que originou o item canônico `CONTROLE P55` — visivelmente ler o item correspondente no JPEG/PDF da nota. Se for de fato "PS5"/"PLAYSTATION 5", **REPROVADO**. Sprint-filha: `sprint_item_p55_rename_canonico.md`.

## Proof-of-work (padrão (u))

```bash
# 1. Localizar NFCe e XMLs correlatos
find data/raw -name "*NFCe*" -o -name "*nfce*" -o -name "*nfc*" | head -10

# 2. Rodar extrator em cada amostra
.venv/bin/python -c "
from src.extractors.nfce_pdf import extrair
from pathlib import Path
r = extrair(Path('data/raw/...'))
print(f'chave_44={r.chave_44}, total={r.total}, itens={len(r.itens)}')
for i in r.itens[:3]:
    print(f'  {i.codigo}: {i.descricao} = R\$ {i.valor_total}')
"

# 3. Cross-check XML
.venv/bin/python -c "
import lxml.etree as ET
tree = ET.parse('data/raw/.../NFCe.xml')
ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
print('total XML:', tree.find('.//nfe:vNF', ns).text)
"

# 4. Investigar item P55
sqlite3 data/output/grafo.sqlite "SELECT nome_canonico, aliases, metadata FROM node WHERE tipo='item' AND (nome_canonico LIKE '%P55%' OR nome_canonico LIKE '%PS5%' OR aliases LIKE '%PS5%')"

# 5. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/ -k nfce -q
```

## Critério de aceitação (gate (z))

1. 2 NFCe processadas.
2. XML cross-check rodado (sucesso ou flag de XML ausente).
3. Cache cresce ≥ 2 entradas com `tipo_documento=nfce_modelo_65`.
4. Relatório `docs/auditorias/VALIDACAO_ARTESANAL_NFCE_<data>.md` com item-a-item.
5. Confirmação ou refutação do bug P55→PS5 com evidência visual (foto do PDF + leitura Opus).
6. Se confirmado: sprint-filha em backlog (`sprint_item_p55_rename_canonico.md`).
7. Gauntlet verde.

## Referência

- Achado original P55→PS5: `docs/auditorias/VALIDACAO_END2END_2026-05-08.md` caso 3.
- Extrator: `src/extractors/nfce_pdf.py`.
- Sprint-pai schema: INFRA-OPUS-SCHEMA-EXTENDIDO.
- DOC-16 (DANFE validar ingestao) — backlog, irmã de NFCe.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase A1.

*"NFCe sem item drill-down é supermercado sem etiqueta de preço — promete análise mas não entrega." — princípio INFRA-VALIDACAO-ARTESANAL-NFCE*
