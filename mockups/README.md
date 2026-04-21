# Mockups Streamlit — Protocolo Ouroboros

Wireframes navegáveis para validar UX das Sprints 20, 51, 52 e 53 **antes** de codar a implementação real.

Dados fictícios determinísticos. Zero consulta ao grafo SQLite ou XLSX de produção. Clique em botões de ação não tem efeito.

## Como rodar

A partir da raiz do projeto:

```bash
.venv/bin/streamlit run mockups/app.py
```

Abre em `http://localhost:8501`. Sidebar navega entre 4 mockups:

- **51 — Catalogação de Documentos** — cards por tipo, timeline mensal, tabela de documentos recentes, painel de conflitos pendentes, gaps de cobertura.
- **52 — Busca Global** — input Spotlight, card de fornecedor agregado, timeline cronológica, listas de documentos/transações/itens.
- **53 — Grafo + Obsidian** — subgrafo interativo de 10 nós, preview de MOC mensal (Markdown com frontmatter + wikilinks), Sankey receita-categoria-fornecedor.
- **20 — Redesign Tipográfico** — comparação antes × depois, paleta Dracula estendida, escala tipográfica de 7 níveis, spacing scale de 6 tokens.

## Rodar em porta alternativa (sem colidir com dashboard real)

```bash
.venv/bin/streamlit run mockups/app.py --server.port 8502
```

## Como capturar screenshot (pipeline validação visual)

```bash
.venv/bin/streamlit run mockups/app.py --server.headless true --server.port 8502 &
SPID=$!
sleep 6
scrot -u /tmp/ouroboros_mockup_$(date +%s).png
kill $SPID
```

Ou via `claude-in-chrome` / `playwright` MCPs (ver `~/.claude/CLAUDE.md` §13-14).

## Estrutura

```
mockups/
├── app.py                           # Entrypoint multi-page com sidebar
├── tema_mockup.py                   # Reexporta tema Dracula + helpers locais
├── pagina_51_catalogacao.py         # Sprint 51
├── pagina_52_busca.py               # Sprint 52
├── pagina_53_grafo_obsidian.py      # Sprint 53
├── pagina_20_redesign.py            # Sprint 20
└── README.md                        # Este arquivo
```

## Isolamento

- `mockups/` vive fora de `src/` — nunca é importado pelo pipeline.
- Nenhum arquivo em `mockups/` consulta `data/output/grafo.sqlite` nem `ouroboros_*.xlsx`.
- Listas literais no topo de cada `pagina_*.py` (`TIPOS_DOCUMENTO`, `FORNECEDOR_DESTAQUE`, etc.).
- Reutiliza `CORES`, `LAYOUT_PLOTLY`, `css_global`, `rgba_cor` de `src/dashboard/tema.py`.

## Próximo passo

Após aprovação visual dos mockups pelo supervisor André, as sprints alvo entram em ciclo normal (`/planejar-sprint` → `/executar-sprint` → `/validar-sprint`) para implementação real em `src/dashboard/paginas/*.py`.
