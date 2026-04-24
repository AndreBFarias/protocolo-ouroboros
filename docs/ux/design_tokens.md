# Design Tokens — Protocolo Ouroboros (proposta Sprint 92)

Consolidação e expansão dos tokens já definidos em `src/dashboard/tema.py`.
Este documento é o **contrato de design** para Sprints 92a/b/c.
Não substitui `tema.py`; declara semântica e regras de uso.

---

## 1. Paleta Dracula — uso declarado

Base já publicada em `DRACULA` e `CORES` (ver `tema.py:19-48`). Semântica proposta
nesta auditoria 2026-04-23:

| Token | Hex | Uso canônico | Uso proibido |
|---|---|---|---|
| `fundo` | `#282A36` | Background principal do app | — |
| `card_fundo` | `#44475A` | Background de cards, sidebar, boxes informativos | Texto (ilegível) |
| `texto` | `#F8F8F2` | Texto primário em fundos escuros | Texto sobre `positivo`/`alerta`/`negativo` (contraste <3:1) |
| `texto_sec` | `#6272A4` | Texto secundário, captions, labels auxiliares | Texto principal em dados críticos |
| `positivo` | `#50FA7B` | Receita, sucesso, saldo positivo saudável, status Pago, saúde >30% | Avisos de aumento de despesa (usar `alerta` ou neutro) |
| `negativo` | `#FF5555` | Despesa principal, atrasos, saldo negativo crítico, Atrasado | Aumento pequeno/esperado (cria falso alarme) |
| `alerta` | `#FFB86C` | Pendente, Questionável, saúde 10-30%, aumento vs mês anterior | Background de textos (contraste ruim) |
| `destaque` | `#BD93F9` | Brand, drill-down ativo, links, borders de elementos focados | Cor de dado quantitativo (reservado p/ UI) |
| `neutro` | `#8BE9FD` | Informação agregada (total), tooltip, placeholder numérico | Alertas (baixo contraste no vermelho) |
| `info` | `#F1FA8C` | Mensagens educativas, notas explicativas | Background de warning (Streamlit já usa amarelo — conflita) |
| `superfluo` | `#FF79C6` | Classificação Supérfluo, ações secundárias, botões "cancelar" | Dados positivos (carrega conotação negativa) |
| `obrigatorio` | `#50FA7B` (alias de positivo) | Classificação Obrigatório | — |
| `questionavel` | `#FFB86C` (alias de alerta) | Classificação Questionável | — |
| `na` | `#6272A4` (alias de texto_sec) | Classificação N/A, transferência interna | — |

---

## 2. Tipografia — escala publicada em tema.py

Decisão: **manter como está.** A escala é consistente e `FONTE_MIN_ABSOLUTA=13`
(Sprint 76) protege o floor.

| Token | px | Uso | Arquivo |
|---|---|---|---|
| `FONTE_MIN_ABSOLUTA` | 13 | Nenhum texto pode ficar abaixo | tema.py:60 |
| `FONTE_LABEL` | 13 | Caption, badge, legenda uppercase | tema.py:62 |
| `FONTE_MINIMA` | 14 | Texto auxiliar | tema.py:61 |
| `FONTE_CORPO` | 15 | Corpo de texto, parágrafos | tema.py:63 |
| `FONTE_SUBTITULO` | 18 | Subtítulos de seção | tema.py:64 |
| `FONTE_TITULO` | 22 | Títulos (h2) | tema.py:65 |
| `FONTE_VALOR` | 24 | Cards KPI — valor principal | tema.py:66 |
| `FONTE_HERO` | 28 | Hero de página (h1) | tema.py:67 |

**Família:** JetBrainsMono ou IBM Plex Mono (já em uso via Streamlit default +
`font-family: monospace` em tokens específicos). Manter.

**Pesos usados:** 400 (regular), 600 (semibold para labels), 700 (bold para
valores e títulos). Não introduzir intermediários (500, 800).

**Tipografia fluida (Sprint 62):** `FLUID_VALOR_KPI`, `FLUID_LABEL_KPI`,
`FLUID_TITULO_GRAFICO` — preservar; cobrem viewport 900px-1600px.

---

## 3. Espaçamento — 8pt grid (tema.py:90-97)

Mantido. Nenhum valor fora deste conjunto é aceito em novos componentes.

| Token | px | Uso |
|---|---|---|
| `SPACING["xs"]` | 4 | Gap entre elementos relacionados (ícone + label) |
| `SPACING["sm"]` | 8 | Gap entre elementos adjacentes (linha de botões) |
| `SPACING["md"]` | 16 | Padding interno de cards, gap entre cards |
| `SPACING["lg"]` | 24 | Margin entre seções (h3 + conteúdo) |
| `SPACING["xl"]` | 32 | Margin entre blocos principais, padding-top da página |
| `SPACING["xxl"]` | 48 | Margin entre clusters de informação distinta |

**Padding canônico de página:** `PADDING_PAGINA_PADRAO_PX=24` (tema.py:74).
Mínimo inviolável: `PADDING_PAGINA_MIN_PX=16`. Novas páginas não podem ir
abaixo.

---

## 4. Iconografia — proposta de introdução

**Hoje:** zero ícones além de caracteres Unicode ocasionais em labels.

**Proposta:** **Feather Icons** (https://feathericons.com) via SVG inline.
Motivos:
- 287 ícones, traço fino, estética mono-linha casa com JetBrainsMono.
- Licença MIT.
- Sem dependência nova (SVG inline, sem CDN, sem webpack).
- Streamlit aceita `st.markdown("<svg>...</svg>", unsafe_allow_html=True)`.

**Inventário mínimo para Sprint 92c (11 ícones):**

| Ícone Feather | Uso | Onde |
|---|---|---|
| `search` | Campo de busca | Busca Global |
| `check-circle` | Doc vinculado | Extrato coluna "Doc?" |
| `alert-triangle` | Doc faltante | Extrato coluna "Doc?" |
| `alert-circle` | Warning geral | Callout warning |
| `info` | Info educativa | Callout info |
| `x` | Remover filtro ativo | Breadcrumb drill-down |
| `zoom-in` | Drill-down disponível | Hover de charts clicáveis |
| `download` | Exportar CSV | Botão de export |
| `external-link` | Abrir doc em preview | Modal de transação |
| `filter` | Filtros avançados | Expander Extrato |
| `calendar` | Período/mês | Sidebar |

**Tamanhos canônicos:**
- `16×16` — inline em texto de corpo
- `20×20` — em botões, labels
- `24×24` — em cards grandes

**Cor:** `currentColor` (herda da cor do texto contexto); modificável via
`color: CORES["destaque"]` no wrapper quando o ícone é standalone/clicável.

---

## 5. Componentes canônicos — estado atual vs proposta

### 5.1 Atual

Helpers em `tema.py`:
- `card_html(titulo, valor, cor)` — card com border-left colorido
- `card_sidebar_html(titulo, valor, cor)` — versão compacta
- `hero_titulo_html(numero, texto, descricao)` — cabeçalho grande de página <!-- noqa: accent (parametro de funcao Python) -->
- `subtitulo_secao_html(texto, cor)` — cabeçalho uppercase com linha sutil
- `label_uppercase_html(texto, cor)` — badge pequeno
- `legenda_abaixo(fig, y, espaco_topo, espaco_base)` — posiciona legenda Plotly

Helper em `src/dashboard/componentes/`:
- `kpi_grid_html(lista)` — grid fluido responsivo

### 5.2 Proposta (Sprint 92c)

Novos helpers ausentes hoje:

| Helper | Assinatura | Substitui |
|---|---|---|
| `callout_html(tipo, mensagem, titulo=None)` | tipo in {"info","warning","error","success"} | `st.warning`/`st.info`/`st.success`/`st.error` |
| `progress_inline_html(pct, cor, label=None)` | 0.0 <= pct <= 1.0 | `st.progress` (que quebra gestalt dos cards Metas) |
| `metric_semantic_html(label, valor, delta=None, cor=None)` | cor auto se delta != 0 | `st.metric` sem semântica visual |
| `icon_html(nome_feather, tamanho=16, cor=None)` | inline SVG | — |
| `breadcrumb_drilldown_html(filtros)` | dict campo->valor | `_renderizar_breadcrumb` de extrato.py (centralizar) |
| `chip_html(texto, cor=None, clicavel=True)` | — | `st.button` quando visual de chip é preferido |

**Critério de aceitação para 92c:** essas 6 funções substituem 100% das
chamadas hoje "custom ad-hoc" em páginas. Grep `<div style=` em `src/dashboard/paginas/`
deve cair de ~50 ocorrências para <= 10 (apenas onde componente custom não faz sentido).

---

## 6. Regras N-para-N (invioláveis)

Estas regras não são opinião; são contratos que o projeto deve respeitar:

1. **Zero emojis.** CLAUDE.md regra #2. Hook guardian.py reforça.
2. **Acentuação PT-BR correta em TUDO.** CLAUDE.md regra #1. Inclui labels do grafo (ver achado Sprint 92 item 1).
3. **Zero `print()` em produção.** CLAUDE.md regra #5. Use `logger`.
4. **Zero menções a IA em commits/código.** CLAUDE.md regra #3.
5. **Nunca hardcoded path.** CLAUDE.md regra #9. Use `Path(__file__).resolve().parents[N]`.
6. **Tema.py é fonte única de cor/tipografia.** Nenhuma página deve hardcodar hex de cor Dracula.
7. **Citação de filósofo como comentário final.** CLAUDE.md regra #10.
8. **N-para-N com chaves de grafo.** <!-- noqa: accent (chaves tecnicas do schema) --> Chaves de dict de grafo são em PT-sem-acento (`"transacao"`, `"descricao"`) — isso é uma EXCEÇÃO documentada em `VALIDATOR_BRIEF.md` §padrões recorrentes. NÃO "corrigir" isso em sprints futuras; faz parte do schema.

---

## 7. Referências externas

- **Nielsen Norman Group — 10 Heuristics:** https://www.nngroup.com/articles/ten-usability-heuristics/
- **WCAG 2.1 Contrast:** https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html (AA: 4.5:1 texto normal, 3:1 UI)
- **Dracula Theme:** https://draculatheme.com/
- **Feather Icons:** https://feathericons.com/
- **8pt Grid:** https://spec.fm/specifics/8-pt-grid
- **Streamlit Theming:** https://docs.streamlit.io/library/advanced-features/theming

---

*"O bom design não é decoração; é a diferença entre o ruído e o sinal." -- princípio de arquitetura da informação*
