# Instruções para Claude Code — Implementação do Redesign Ouroboros

> Documento operacional. Lê-se de cima para baixo, executa-se em ordem.
> Cada bloco é uma sprint pequena (≤2h). Não pular.

## 0. Antes de começar

- Branch: `git checkout -b ux/redesign-v1`
- Pré-requisito: backup do `src/dashboard/tema.py` atual em `tema.legacy.py`
- Os tokens canônicos vivem em `ouroboros-redesign-v1/tokens/*.json`. Toda mudança de cor/tipografia/espaço passa por lá primeiro.

## 1. Migrar `tema.py` para tokens novos

Substituir as constantes em `src/dashboard/tema.py`:

```python
# Backward-compat: aliases preservam nomes existentes (fundo, card_fundo, texto…)
COLOR = {
    # bg
    "fundo":         "#0e0f15",   # antes #282A36
    "card_fundo":    "#1a1d28",   # antes #44475A
    "card_elevado":  "#232735",   # NOVO
    "fundo_inset":   "#0a0b10",   # NOVO

    # texto
    "texto":         "#f8f8f2",
    "texto_sec":     "#a8a9b8",   # NOVO — para metadados, datas
    "texto_muted":   "#6c6f7d",   # NOVO — para placeholders

    # acentos (mantém Dracula)
    "destaque":   "#bd93f9",
    "positivo":   "#50fa7b",
    "negativo":   "#ff5555",
    "alerta":     "#ffb86c",
    "neutro":     "#8be9fd",
    "info":       "#f1fa8c",
    "superfluo":  "#ff79c6",

    # NOVO — D7 (cobertura observável)
    "d7_graduado":   "#6b8e7f",
    "d7_calibracao": "#f1fa8c",
    "d7_regredindo": "#ffb86c",
    "d7_pendente":   "#6c6f7d",

    # NOVO — validação humana
    "humano_aprovado":  "#6b8e7f",
    "humano_rejeitado": "#ff5555",
    "humano_revisar":   "#f1fa8c",
}
```

Atualizar `.streamlit/config.toml` com o conteúdo de `streamlit-theme/config.toml`.

## 2. Sidebar nova com 6 clusters

Editar `src/dashboard/app.py`. Substituir o seletor de páginas por um `st.sidebar` agrupado:

```python
CLUSTERS = [
    ("Inbox",        ["inbox"]),
    ("Home",         ["visao_geral"]),
    ("Finanças",     ["extrato", "contas", "pagamentos", "projecoes"]),
    ("Documentos",   ["busca_global", "catalogacao", "completude", "revisor", "validacao_arquivos"]),
    ("Análise",      ["categorias", "analise", "irpf"]),
    ("Metas",        ["metas"]),
]
```

Sob cada cluster, listar páginas com `st.page_link()`. A página ativa fica destacada via CSS injection (vide `_components/sidebar.py`).

## 3. Adicionar página Inbox

- Criar `src/dashboard/paginas/inbox.py`
- Componentes: `dropzone()`, `fila_arquivos()`, `drawer_sidecar()`, `bloco_skill_instrucao()`
- Lê de `data/inbox/*.{pdf,csv,xlsx,ofx,jpg,png}` e `data/inbox/.extracted/*.json`
- A "skill" é texto estático — instrução para humano abrir Claude Code CLI

## 4. Refatorar `validacao_arquivos.py`

- Layout em 4 zonas: paridade global (tiles por tipo), filtros, tabela densa, diff lado-a-lado
- Adicionar coluna `valor_opus` ao schema (já existe `valor_etl`, `valor_humano`)
- Adicionar coluna `confianca_opus` (float 0..1)
- Drawer com diff JSON syntax-highlighted

## 5. Refatorar `revisor.py`

- 4 colunas: OFX original, rascunho ETL, Opus, humano
- Cores: green / yellow / purple / pink (border-left)
- Mantém schema atual (data, valor, itens, fornecedor, pessoa)

## 6. Página IRPF

- Compila tags fiscais a partir do banco catalogado
- Tags: rendimento_tributavel, rendimento_isento, dedutivel_medico, dedutivel_educacional, previdencia_privada, imposto_pago, inss_retido, doacao_dedutivel
- Card lateral: pacote final (PDF + XLSX + JSON + originais), checklist, botão "Gerar pacote"

## 7. Atalhos de teclado

Injetar via `st.markdown` + componente JS:
- `g h` → Visão Geral · `g i` → Inbox · `g v` → Validação · `g r` → Revisor · `g f` → IRPF · `g c` → Catalogação
- `/` → focar busca · `?` → modal de ajuda

## 8. Critério de pronto (D7)

- [ ] Tema migrado, todos os testes existentes passam (`pytest`)
- [ ] Sidebar com 6 clusters renderiza sem flicker
- [ ] Inbox lista arquivos reais de `data/inbox/`
- [ ] Validação carrega `data/output/validacao_arquivos.csv` no novo layout
- [ ] Revisor mantém compatibilidade com Sprint D2
- [ ] IRPF gera pacote em `data/aplicacoes/irpf_2026/`
- [ ] Atalhos de teclado funcionam em todas as páginas

## Princípios não-negociáveis

1. **Tokens são lei.** Nenhum hex hardcoded fora de `tokens/`.
2. **Backward-compat por aliases.** Páginas legacy continuam usando `fundo`, `card_fundo` etc.
3. **D7 é cobertura, não gate.** Skills regredindo aparecem em destaque, mas não bloqueiam pipeline.
4. **Humano-no-loop é deliberado.** ADR-13. Sem cron, sem API externa do Claude.
5. **sha256 é canônico.** Toda referência a arquivo usa sha8 visível + sha256 completo no sidecar.
