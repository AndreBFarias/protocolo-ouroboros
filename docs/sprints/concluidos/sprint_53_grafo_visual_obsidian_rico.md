---
concluida_em: 2026-04-21
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 53
  title: "Grafo Visual Interativo + Obsidian Rico"
  touches:
    - path: src/dashboard/paginas/grafo.py
      reason: "pyvis/streamlit-agraph renderiza subgrafo navegável"
    - path: src/obsidian/sync.py
      reason: "expande sync para criar notas Vida-de-Documento com links bidirecionais"
    - path: src/obsidian/templates/
      reason: "templates markdown para documento, fornecedor, item"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_obsidian_rico.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Dashboard tem página Grafo com subgrafo do fornecedor selecionado (limite 100 nós)"
    - "Obsidian vault ganha pastas Documentos/, Fornecedores/, Itens/ com notas linkadas"
    - "Nota Documento tem frontmatter completo + backlinks para transações/itens"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 53 -- Grafo Visual + Obsidian Rico

**Status:** CONCLUÍDA
**Data:** 2026-04-19
**Prioridade:** MEDIA
**Tipo:** Feature
**Dependências:** Sprints 42 (grafo), 52 (busca)
**Desbloqueia:** UX final
**Issue:** --
**ADR:** ADR-12

---

## Como Executar

- `make dashboard` → Grafo
- `./run.sh --sync`
- `.venv/bin/pytest tests/test_obsidian_rico.py`

### O que NÃO fazer

- NÃO renderizar grafo inteiro (milhares de nós trava) -- subgrafo com radius máximo
- NÃO duplicar notas existentes no Obsidian -- idempotência

---

## Problema

Grafo como estrutura é poderoso mas ilegível em linha de comando. Usuário precisa:
- Ver visualmente quem se conecta a quem
- Navegar em Obsidian entre Documento → Item → Fornecedor
- Compartilhar snapshots (foto do subgrafo) como evidência

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Obsidian sync | `src/obsidian/sync.py` | Gera notas mensais (Sprint 06) |
| Grafo queries | `src/graph/queries.py` | Subgrafo por entidade |
| Streamlit | `make dashboard` | App rodando |

## Implementação

### Fase 1: grafo visual

Escolha: `streamlit-agraph` (leve) ou `pyvis` (render HTML embedded). Decisão interna, pesar peso vs riqueza.

```python
def renderizar_subgrafo(entidade_id: int, profundidade: int = 2, max_nos: int = 100):
    nos, arestas = _subgrafo_bfs(entidade_id, profundidade, max_nos)
    # cor por tipo, tamanho por grau
    return Config(height=600), nos, arestas
```

### Fase 2: Obsidian rico

Estrutura nova do vault:

```
Ouroboros/
├── Documentos/
│   ├── NF_20260408_Americanas_12345.md
│   └── ...
├── Fornecedores/
│   ├── Neoenergia.md
│   └── ...
├── Itens/
│   ├── Desodorante-Dove-150ml.md
│   └── ...
├── Transacoes/  (já existia)
└── Meses/       (já existia)
```

### Fase 3: templates

`src/obsidian/templates/documento.md.j2`:

```markdown
---
tipo: documento
documento_id: {{ id }}
data: {{ data }}
fornecedor: "[[{{ fornecedor_nome }}]]"
total: {{ total }}
categoria_transacao: "[[{{ categoria }}]]"
tags: [nf, {{ tipo_documento }}]
---

# {{ descricao_curta }}

**Data:** {{ data }}
**Fornecedor:** [[{{ fornecedor_nome }}]]
**Total:** R$ {{ total }}

## Itens ({{ itens | length }})

{% for item in itens -%}
- [[{{ item.canonico }}]] x {{ item.qtd }} = R$ {{ item.total }}
{% endfor %}

## Transação vinculada

{% if transacao_id -%}
- [[Transacao_{{ transacao_id }}]]
{% else -%}
_(sem linking confirmado)_
{% endif %}

## Arquivo original

![[{{ caminho_arquivo }}]]
```

Idem para fornecedor e item.

### Fase 4: idempotência

Cada sincronização:
1. Lê grafo
2. Para cada node de interesse (documento, fornecedor, item) gera nota
3. Escreve com `frontmatter` estável (chave: updated_at do node)
4. Se nota já existe com mesmo updated_at, pula

### Fase 5: testes

- `test_renderiza_subgrafo_tamanho_limitado`
- `test_cria_nota_documento_com_frontmatter`
- `test_backlinks_bidirecionais` (fornecedor -> documento e vice-versa)
- `test_sync_idempotente_nao_sobrescreve`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A53-1 | Obsidian não gosta de `[[Link]]` com caracteres especiais | Slugify nomes (ASCII) antes de usar em link |
| A53-2 | pyvis cria HTML absoluto que estoura Streamlit | `height=600` explícito + wrap em `components.html` |
| A53-3 | Notas sobrescrevem manualmente editadas pelo usuário | Adicionar `#sincronizado-automaticamente` em tags; se usuário remover, não sobrescreve |
| A53-4 | Paths com espaço no vault Obsidian quebram embed | `![[...]]` com path relativo ao vault, não ao projeto |

## Evidências Obrigatórias

- [ ] Testes passam
- [ ] Obsidian vault tem Documentos/, Fornecedores/, Itens/ populados
- [ ] Links bidirecionais funcionam (visualização de gráfico do Obsidian)
- [ ] Dashboard renderiza subgrafo sem erro

## Verificação end-to-end

```bash
./run.sh --sync
ls $OBSIDIAN_VAULT/Ouroboros/Documentos/ | head
make dashboard &
# abrir Grafo com uma entidade no filtro
```

## Conferência Artesanal Opus

**Arquivos originais a ler:** notas geradas no vault + subgrafo visualizado.

**Checklist:**

1. Notas têm frontmatter completo e válido?
2. Links bidirecionais navegáveis no Obsidian?
3. Subgrafo no dashboard é legível (não super denso)?

**Relatório em `docs/propostas/sprint_53_conferencia.md`**: ajustes de layout e templates.

**Critério**: humano consegue navegar "foto → NF → item → fornecedor → outra NF" sem tocar no terminal.

---

*"O grafo é mapa; o Obsidian é diário." -- princípio do navegador*
