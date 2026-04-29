---
concluida_em: 2026-04-22
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 71
  title: "Sync rico bidirecional: Ouroboros escreve em ~/Controle de Bordo/Pessoal/Casal/Financeiro/"
  touches:
    - path: src/obsidian/sync.py
      reason: "estender sync além do mensal: gerar notas por documento/fornecedor"
    - path: src/obsidian/templates/
      reason: "templates Jinja2 para documento, fornecedor, transacao"
    - path: src/integrations/controle_bordo.py
      reason: "path builder para Pessoal/Casal/Financeiro"
    - path: tests/test_obsidian_rico_vault.py
      reason: "teste com vault sintético"
  n_to_n_pairs: []
  forbidden:
    - "Sobrescrever notas que o usuário editou manualmente (respeitar tag #sincronizado-automaticamente)"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_obsidian_rico_vault.py -v"
      timeout: 60
  acceptance_criteria:
    - "Para cada documento no grafo, existe nota em ~/Controle de Bordo/Pessoal/Casal/Financeiro/Documentos/{YYYY-MM}/{slug}.md"
    - "Para cada fornecedor com >=2 docs, existe nota em Pessoal/Casal/Financeiro/Fornecedores/{slug}.md"
    - "Notas têm frontmatter válido: tipo, id, data, fornecedor, valor, tags, arquivo_original (wikilink para _Attachments/)"
    - "Arquivo original copiado para Pessoal/Casal/Financeiro/_Attachments/ (preserva no vault)"
    - "Link bidirecional: Documento -> Fornecedor -> Meses -> Transacao (grafo Obsidian nativo mostra)"
    - "Notas editadas manualmente não são sobrescritas (detecta tag #sincronizado-automaticamente ou frontmatter `sincronizado: true`)"
    - "Sync é idempotente: 2 execuções consecutivas não mudam arquivos"
  proof_of_work_esperado: |
    BORDO_DIR=/tmp/vault_teste .venv/bin/python -m src.obsidian.sync --rico
    ls /tmp/vault_teste/Pessoal/Casal/Financeiro/Documentos/2026-04/
    # esperado: notas .md com frontmatter completo
    # segunda rodada: timestamps não mudam
    BORDO_DIR=/tmp/vault_teste .venv/bin/python -m src.obsidian.sync --rico
    # diff antes/depois esperado: zero
```

---

# Sprint 71 — Sync rico bidirecional

**Status:** CONCLUÍDA (2026-04-22)
**Prioridade:** P1
**Dependências:** Sprint 70 (adapter existe), ADR-18 aprovado
**Issue:** INTEGRACAO-02 <!-- noqa: accent -->


## Problema

Sprint 06 criou sync Obsidian unidirecional que só gera notas mensais agregadas. Não gera nota por documento, nem por fornecedor, nem linka originais. A visão do Andre: navegar no Obsidian tipo o grafo que ele já tem (imagens 9-11), clicando em "Natação" e chegando ao boleto.

## Implementação

### Templates Jinja2

`src/obsidian/templates/documento.md.j2`:

```markdown
---
tipo: documento
documento_id: {{ id }}
data: {{ data }}
fornecedor: "[[{{ fornecedor_slug }}]]"
valor: {{ valor }}
categoria: "[[{{ categoria_slug }}]]"
tipo_documento: {{ tipo_documento }}
transacao_ids: {{ transacao_ids | tojson }}
arquivo_original: "[[_Attachments/{{ arquivo_nome }}]]"
tags: [sincronizado-automaticamente, documento, {{ tipo_documento }}]
sincronizado: true
created: {{ data }}
modified: {{ data_mod }}
---

# {{ descricao_curta }}

**Data:** {{ data }}
**Fornecedor:** [[{{ fornecedor_slug }}]]
**Valor:** R$ {{ valor | formatar_brl }}
**Tipo:** {{ tipo_documento }}

## Itens ({{ itens | length }})

{% for item in itens -%}
- [[{{ item.canonico_slug }}]] x {{ item.qtde }} = R$ {{ item.valor_total | formatar_brl }}
{% endfor %}

## Transações vinculadas

{% if transacao_ids -%}
{% for tx_id in transacao_ids -%}
- [[Transacao_{{ tx_id }}]]
{% endfor %}
{% else -%}
_Sem vinculo ainda. Veja [[Gap Analysis]] para jogar comprovante na inbox._
{% endif %}

## Arquivo original

![[_Attachments/{{ arquivo_nome }}]]

---
*Gerado automaticamente por Ouroboros. Para editar manualmente, remova a tag `#sincronizado-automaticamente` antes.*
```

Idem para `fornecedor.md.j2`, `transacao.md.j2`.

### Detecção de edição manual

Antes de sobrescrever:

```python
def eh_seguro_sobrescrever(nota_path: Path) -> bool:
    if not nota_path.exists():
        return True
    conteudo = nota_path.read_text()
    # Tag explícita presente OU frontmatter sincronizado: true
    return "#sincronizado-automaticamente" in conteudo or "sincronizado: true" in conteudo
```

### Path builder

`Pessoal/Casal/Financeiro/` tem subpastas:
- `Documentos/{YYYY-MM}/{slug}.md`
- `Fornecedores/{slug}.md`
- `Itens/{slug}.md` (opcional, só se item tem >=2 docs)
- `Meses/{YYYY-MM}.md` (MOC mensal)
- `_Attachments/` (PDFs/JPGs dos originais)

### Cópia de originais

Copia do `data/raw/originais/{hash}.ext` para `~/Controle de Bordo/Pessoal/Casal/Financeiro/_Attachments/{nome_canonico}.ext`.

## Armadilhas

| A71-1 | Vault tem limite 1GB (Obsidian Sync) | Anexos grandes (>5MB) ficam só em `data/raw/originais/` e a nota tem link absoluto, não wikilink |
| A71-2 | Caracteres especiais no slug quebram wikilinks | Slugify ASCII + limite 80 chars |
| A71-3 | Edição em conflito com Obsidian aberto | Skip com warning se lockfile detectado |

## Evidências

- [x] `src/obsidian/sync_rico.py` (~310L): módulo novo que escreve em `$BORDO_DIR/Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/`.
- [x] `eh_seguro_sobrescrever()` detecta tag `#sincronizado-automaticamente` ou frontmatter `sincronizado: true`; sem um dos dois, a nota é preservada (soberania do usuário).
- [x] `_conteudo_mudou()` + `_hash_conteudo()` garantem idempotência: segunda execução sobre mesmo grafo não reescreve arquivo inalterado.
- [x] `sincronizar_rico(vault_root, grafo_path, dry_run, min_docs_por_fornecedor)` como API pública + CLI `python -m src.obsidian.sync_rico [--executar] [--vault PATH]`.
- [x] Template de documento embeda wikilink `![[_Attachments/{slug}.ext]]` e backlinks para `[[Fornecedores/...]]`.
- [x] Template de fornecedor inclui bloco Dataview que lista documentos via query `WHERE fornecedor = "[[Fornecedores/{slug}]]"`.
- [x] `_copiar_original()` copia `data/raw/originais/{hash}.ext` para `_Attachments/` do vault.
- [x] Forbidden zones do vault respeitadas (módulo nunca lê/escreve em `.sistema/`, `Trabalho/`, `Segredos/`, `Arquivo/`).
- [x] 19 testes em `tests/test_obsidian_rico_vault.py`: slug, yyyymm, soberania, render, idempotência, edição manual, grafo ausente. Baseline 955 → 974 passed (+19).
- [x] Gauntlet: make lint exit 0, smoke 8/8 OK.

### Ressalvas

- [R71-1] A cópia de originais usa o campo `arquivo_original` do metadata do node, que nem sempre está presente em nodes ingeridos por extratores antigos. Para esses, o `![[...]]` aponta para um caminho inexistente no vault até uma próxima rodada de reprocessamento que preencha `arquivo_original` absoluto. Não bloqueia a sprint; é débito herdado dos extratores.
- [R71-2] Notas `Meses/{YYYY-MM}.md` (MOC mensal) não foram implementadas nesta sprint — o `sync.py` original já gera uma versão disso via `gerar_moc_mensal`, que vive em `Pessoal/Financeiro/Relatorios/` (caminho antigo, não `Pessoal/Casal/Financeiro/Meses/`). Migração para o novo caminho fica como débito explícito (sprint futura).
- [R71-3] Volume atual do grafo é pequeno (2 documentos, 1 fornecedor com docs suficientes quando `min_docs=2`). Cobertura de caso funcional real depende de reprocessamento em volume.

---

*"O grafo do vault é o nosso dashboard sempre aberto." — princípio"*
