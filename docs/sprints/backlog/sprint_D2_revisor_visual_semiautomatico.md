## 0. SPEC (machine-readable)

```yaml
sprint:
  id: D2
  title: "Revisor Visual Semi-Automatizado -- substitui Sprint AUDITORIA-ARTESANAL-FINAL"
  prioridade: P0
  estimativa: 6-8h
  origem: "auditoria 2026-04-26 -- supervisor pediu sistema visual em vez de revisão CLI 1-a-1"
  substitui:
    - "docs/sprints/backlog/sprint_AUDITORIA_ARTESANAL_FINAL.md"
  touches:
    - path: src/dashboard/paginas/revisor.py
      reason: "nova página da cluster Documentos"
    - path: src/dashboard/app.py
      reason: "registra nova aba Revisor"
    - path: src/dashboard/dados.py
      reason: "função listar_pendencias_revisao(grafo, raw)"
    - path: tests/test_revisor.py
      reason: "cobertura testes da nova página + função"
    - path: data/output/revisao_humana.sqlite
      reason: "armazena marcações persistentes (criado em runtime, no .gitignore)"
    - path: docs/revisoes/<data>.md
      reason: "relatório consolidado por sessão"
  forbidden:
    - "Mover/deletar arquivos brutos durante revisão (revisor é read-only no data/raw/)"
    - "Usar st.experimental_rerun em loop -- causa ciclo Streamlit"
    - "Persistir marcações em JSON ou YAML (deve ser SQLite por consistência com grafo.sqlite)"
    - "Ignorar PII -- relatório final mascara CPFs/CNPJs antes de salvar"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_revisor.py -v"
    - cmd: "make smoke"
    - cmd: "test -f src/dashboard/paginas/revisor.py"
  acceptance_criteria:
    - "Página Revisor lista pendências em data/raw/_classificar/, _conferir/, e nodes do grafo com confidence < 0.8"
    - "Para cada item: foto/PDF original em iframe (reusando preview_documento.py Sprint 74) + JSON estruturado lado-a-lado"
    - "Checkboxes por dimensão: data correta, valor correto, itens corretos, fornecedor correto, pessoa correta"
    - "Marcações persistem em data/output/revisao_humana.sqlite com schema revisao(item_id, dimensao, ok BOOLEAN, observacao TEXT, ts)"
    - "Botão 'Gerar relatório' produz docs/revisoes/<YYYY-MM-DD>.md com taxa de fidelidade humana e ressalvas"
    - "PII mascarada no relatório (regex CPF/CNPJ) antes de gravar"
    - "Ao supervisor aprovar padrão novo (ex: regra YAML para classificar X), botão 'Sugerir patch' abre diff em mappings/*.yaml para copy-paste"
    - "Pelo menos 8 testes unitários em test_revisor.py cobrindo: listagem, persistência SQLite, geração relatório, mascaramento PII"
  proof_of_work_esperado: |
    # Antes
    ls data/raw/_classificar/ | wc -l   # 3 PDFs aguardando revisão
    ls data/raw/_conferir/    | wc -l   # 2 cupons aguardando
    
    # Rota
    ./run.sh --dashboard
    # Navegar: cluster Documentos -> aba Revisor
    # Para cada pendência: clicar nas dimensões corretas, salvar
    
    # Depois (em sessão de exemplo)
    sqlite3 data/output/revisao_humana.sqlite "SELECT COUNT(*) FROM revisao;"
    # = 25 marcações (5 itens x 5 dimensões)
    
    cat docs/revisoes/2026-XX-XX.md
    # Taxa de fidelidade: 80% (20/25 OK)
    # Ressalvas listadas item-a-item
```

---

# Sprint D2 -- Revisor Visual Semi-Automatizado

**Status:** BACKLOG (P0, criado 2026-04-26)
**Substitui:** `sprint_AUDITORIA_ARTESANAL_FINAL.md` (revisão 1-a-1 inviável em 760 arquivos)

## Motivação

Supervisor explicitou em 2026-04-26: "queria um sistema de validação semi automatizado, usando streamlit mostrando a foto, o pdf e o extraído de forma que eu vá marcando e saibamos os problemas. Pode ser as mesmas que vc analisar e classificar, vai ser bom pra alinharmos as visões homem máquina."

Sprint original (Sprint AUDITORIA-ARTESANAL-FINAL) propõe revisão CLI 1-a-1 de ~760 arquivos = inviável (25h+ de sessão humana). Esta sprint substituta:
- Marcação visual lado-a-lado (foto/PDF + JSON extraído).
- 30 segundos por item em vez de 2 min.
- 760 arquivos = 6.5h.
- Persiste marcações para gerar sprints-filhas automáticas quando supervisor descobre padrão recorrente.

Subproduto importante: alinhamento homem-máquina mensurável. Sistema mostra o que ele acha que extraiu; humano confirma ou nega; divergências viram regras YAML novas.

## Escopo

### Fase 1 -- Listagem de pendências

Função `listar_pendencias_revisao(grafo, raw)` em `src/dashboard/dados.py`:
- Pega arquivos em `data/raw/_classificar/` (não-classificados).
- Pega arquivos em `data/raw/_conferir/` (fallback supervisor recall < 80%).
- Pega nodes do grafo com `confidence < 0.8` (heurística do extrator).
- Pega documentos sem aresta `documento_de` (achado P0 da auditoria 2026-04-26: 41 docs com 0% linkados).
- Pega NFC-es duplicadas por chave_44 quase igual (achado P1: nodes 7464 vs 7466).
- Retorna lista ordenada por prioridade.

### Fase 2 -- Página Streamlit

Nova `src/dashboard/paginas/revisor.py` (~300L):
- Header de hero `hero_titulo_html("Revisor", "Validação visual de extrações ambíguas", numero=99)`.
- KPI cards: total pendências, % validados, % rejeitados, % aguardando.
- Loop por pendência:
  - Layout de 2 colunas (60/40 ou 50/50):
    - **Esquerda:** preview do arquivo original (iframe data URL via `preview_documento.py` da Sprint 74).
    - **Direita:** JSON estruturado do que o extrator viu (data, valor, itens, fornecedor, pessoa).
  - Abaixo: checkboxes por dimensão (data, valor, itens[N], fornecedor, pessoa). Cada uma: `[OK] [erro] [não-aplicável]` + campo texto livre para observação.
  - Botões: "Salvar marcações", "Próxima pendência", "Pular".
- Sidebar lateral: filtros (tipo de pendência, mês, pessoa).

### Fase 3 -- Persistência

Schema SQLite em `data/output/revisao_humana.sqlite` (no .gitignore):

```sql
CREATE TABLE revisao (
    item_id TEXT NOT NULL,
    dimensao TEXT NOT NULL,
    ok INTEGER NOT NULL,        -- 1=OK, 0=erro, NULL=não-aplicável
    observacao TEXT,
    ts TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (item_id, dimensao)
);
CREATE INDEX idx_revisao_ts ON revisao (ts);
CREATE INDEX idx_revisao_dimensao ON revisao (dimensao);
```

`item_id` é o caminho relativo (`data/raw/_classificar/X.pdf`) ou node id do grafo (`node_42`).

### Fase 4 -- Geração de relatório

Botão "Gerar relatório da sessão" produz `docs/revisoes/<YYYY-MM-DD>.md` com:
- Taxa de fidelidade humana global (% de dimensões marcadas OK).
- Detalhe por item revisado: caminho, tipo, dimensões aprovadas/reprovadas, observação.
- **PII mascarada** (regex CPF `\d{3}\.\d{3}\.\d{3}-\d{2}` -> `XXX.XXX.XXX-XX`; CNPJ `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}` -> `XX.XXX.XXX/0001-XX`).
- Lista de padrões recorrentes detectados (ex: "5 cupons foram marcados como tendo `data` errada e todos têm OCR < 600 chars" -> proposta de regra nova).

### Fase 5 -- Sugestor de patch

Ao identificar padrão recorrente (3+ pendências com mesma dimensão errada), botão "Sugerir patch":
- Abre modal com diff proposto em `mappings/<arquivo>.yaml` para copy-paste.
- Não aplica automaticamente (regra: humano sempre aprova edits manualmente).

## Armadilhas

- **Streamlit st.dialog não permite iframe de PDF diretamente** -- precisa renderizar como base64 inline (já testado em Sprint 74).
- **Volume real pode esgotar memória do navegador** se carregar 760 PDFs simultaneamente. Solução: paginação (10 por vez).
- **PII em logs do Streamlit** -- garantir que `st.write()` não mostra observações em log (achado P1-A26-02 da auditoria).
- **SQLite em `data/output/`** -- garantir que `.gitignore` cobre o arquivo.
- **Deduplicar pendências entre rodadas** -- se mesmo item já foi revisado em sessão anterior, não listar de novo (filtrar por `ts >`).

## Dependências

- Sprint 74 (modal_transacao + preview_documento) -- já concluída, fornece `preview_documento.py`.
- Sprint 87.2 (coluna Doc? + identificador) -- já concluída, fornece hash canônico.
- Não depende das Sprints 95/96/97 (P0 do dia) -- pode rodar em paralelo.

## Valor

Quando a Sprint D2 fechar, o casal terá:
- Validação humana sustentável (6.5h vs 25h+).
- Alinhamento homem-máquina mensurável (taxa de fidelidade explícita).
- Novas regras YAML descobertas em sessão (padrões recorrentes -> patches Edit-pronto).
- Substrato para confiar no XLSX/grafo antes de avançar para Sprint OMEGA (94).

---

*"A revisão visual é a ponte entre intuição humana e automação determinística." -- princípio do alinhamento mensurável*
