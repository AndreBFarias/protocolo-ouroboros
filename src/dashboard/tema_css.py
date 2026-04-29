"""CSS global do dashboard Dracula (extraído de tema.py).

Sprint ANTI-MIGUE-08: o bloco ``css_global()`` ficou com >500 linhas
e dominava ``tema.py``. Movido para módulo dedicado, re-exportado pelo
módulo ``tema`` para preservar contratos públicos
(``from src.dashboard.tema import css_global``).

Tokens (CORES, SPACING, fontes, paddings, breakpoints) continuam
declarados em ``tema.py`` e são consumidos aqui via import explícito.
"""

from __future__ import annotations

from src.dashboard.tema import (
    BORDA_ATIVA_PX,
    BORDA_RAIO,
    BREAKPOINT_COMPACTO,
    BREAKPOINT_MINIMO,
    CORES,
    FLUID_LABEL_KPI,
    FLUID_VALOR_KPI,
    FONTE_CORPO,
    FONTE_HERO,
    FONTE_LABEL,
    FONTE_MIN_ABSOLUTA,
    FONTE_SUBTITULO,
    FONTE_TITULO,
    PADDING_CHIP,
    PADDING_INTERNO,
    SPACING,
)


def css_global() -> str:
    """Retorna bloco CSS global para o dashboard Dracula.

    Sprint 92c: publica CSS custom properties em ``:root`` a partir dos tokens
    Python já existentes (``CORES``, ``SPACING``, fontes). Helpers HTML novos
    (callout, progress_inline, metric_semantic, breadcrumb) referenciam esses
    tokens via ``var(--color-*)`` em vez de interpolar hex, permitindo que
    temas futuros sobrescrevam apenas o bloco ``:root`` sem tocar em helper
    algum. Componentes Plotly continuam usando hex direto pois JSON inline
    não resolve ``var()``.
    """
    return f"""
    <style>
    :root {{
        --color-fundo: {CORES["fundo"]};
        --color-card-fundo: {CORES["card_fundo"]};
        --color-texto: {CORES["texto"]};
        --color-texto-sec: {CORES["texto_sec"]};
        --color-positivo: {CORES["positivo"]};
        --color-negativo: {CORES["negativo"]};
        --color-alerta: {CORES["alerta"]};
        --color-destaque: {CORES["destaque"]};
        --color-neutro: {CORES["neutro"]};
        --color-info: {CORES["info"]};
        --color-superfluo: {CORES["superfluo"]};
        --color-obrigatorio: {CORES["obrigatorio"]};   /* noqa: accent (CSS ident ASCII) */
        --color-questionavel: {CORES["questionavel"]}; /* noqa: accent (CSS ident ASCII) */
        --spacing-xs: {SPACING["xs"]}px;
        --spacing-sm: {SPACING["sm"]}px;
        --spacing-md: {SPACING["md"]}px;
        --spacing-lg: {SPACING["lg"]}px;
        --spacing-xl: {SPACING["xl"]}px;
        --spacing-xxl: {SPACING["xxl"]}px;
        --font-min: {FONTE_MIN_ABSOLUTA}px;
        --font-label: {FONTE_LABEL}px;
        --font-corpo: {FONTE_CORPO}px;
        --font-subtitulo: {FONTE_SUBTITULO}px;
        --font-titulo: {FONTE_TITULO}px;
        --font-hero: {FONTE_HERO}px;
        --padding-interno: {PADDING_INTERNO}px;
        --padding-chip: {PADDING_CHIP}px;
        --borda-raio: {BORDA_RAIO}px;
        --borda-ativa-px: {BORDA_ATIVA_PX}px;
    }}
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        font-size: {FONTE_CORPO}px;
    }}
    /* Sprint 76: floor absoluto de {FONTE_MIN_ABSOLUTA}px. Impede que regras
       herdadas ou inline reduzam texto abaixo do legível. Aplicado via
       seletor universal sem !important para respeitar hierarquia quando
       a classe alvo define valor >= {FONTE_MIN_ABSOLUTA}px. */
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] span,
    [data-testid="stAppViewContainer"] li,
    [data-testid="stAppViewContainer"] label {{
        font-size: max({FONTE_MIN_ABSOLUTA}px, 1em);
    }}
    .js-plotly-plot .plotly text {{
        font-size: {FONTE_MIN_ABSOLUTA}px !important;
    }}
    /* Sprint 76 + Sprint UX-116: padding interno generoso nos retângulos
       das páginas, evitando texto colado na borda em Grafo/IRPF/Metas/Extrato.
       UX-116 substitui o shorthand da Sprint 76 por 4 declarações explícitas
       padding-{{top,right,bottom,left}} para tornar o contrato testável
       direção por direção e garantir respiro nos 4 lados em todas as abas. */
    .main .block-container {{
        padding-top: {PADDING_INTERNO}px !important;
        padding-right: {PADDING_INTERNO}px !important;
        padding-bottom: {PADDING_INTERNO}px !important;
        padding-left: {PADDING_INTERNO}px !important;
    }}
    /* Sprint UX-125 AC1: body 100% horizontal -- Streamlit por padrão aplica
       max-width restritivo (~736px ou 1200px conforme tema) ao
       .block-container, deixando faixa preta à direita do conteúdo em
       monitores wide. Forçamos max-width: 100% e width: 100% para que o
       conteúdo ocupe toda a viewport. Regra separada do bloco de padding
       (acima) para preservar regex de testes legados (test_ux_tokens
       ::test_css_global_declara_padding_bloco) que casa o seletor seguido
       imediatamente de uma declaração de padding. Aplicado também no
       testid moderno [data-testid="stMainBlockContainer"] (>=1.32). */
    .main .block-container,
    [data-testid="stMainBlockContainer"] {{
        max-width: 100% !important;
        width: 100% !important;
    }}
    .block-container {{ padding-top: {SPACING["xl"]}px; }}
    /* Sprint UX-115 + Sprint UX-119 AC14 (unificação de cor): o container
       externo do conteúdo principal ([data-testid="stMain"]) ficava em
       cor de fundo Dracula (color-fundo) por default, criando faixa
       vertical à esquerda e faixa inferior em volta do bloco interno.
       UX-115 pintou com literal próximo (gambiarra); UX-119 troca por
       var(--color-card-fundo) -- token CORES['card_fundo']. Resultado:
       stMain e sidebar ficam exatamente no mesmo tom, eliminando a
       diferença de 1 ponto no canal verde que o dono detectou.
       Sobrescreve apenas este seletor; não afeta fundo da app inteira
       (html/body continuam regidos por --color-fundo). */
    [data-testid="stMain"] {{
        background-color: var(--color-card-fundo);
    }}
    /* Sprint UX-118: faixas escuras residuais (#282A36 padrão Dracula) que
       apareciam no contorno do app são cobertas trocando o fundo do
       container raiz [data-testid="stApp"] por --color-card-fundo
       (#44475A). Tokens CORES['fundo'] e DRACULA['background'] permanecem
       intocados; apenas o seletor stApp passa a usar o tom card. */
    [data-testid="stApp"] {{
        background-color: var(--color-card-fundo) !important;
    }}
    /* Sprint UX-119 AC2: status widget e toast da Streamlit (top warning bar
       que mostra avisos como `--no-sandbox`, deprecation warnings, etc.)
       herdam fundo escuro #282A36 e destoam da paleta unificada. Pintamos
       com var(--color-card-fundo) para alinhar ao restante do app.
       stStatusWidget cobre o status de execução (canto superior direito);
       stToast cobre toasts efêmeros; stAlertContainer cobre alertas em
       containers; stHeader cobre a top bar onde a deprecation aparece. */
    [data-testid="stStatusWidget"],
    [data-testid="stToast"],
    [data-testid="stAlertContainer"],
    [data-testid="stHeader"] {{
        background-color: var(--color-card-fundo) !important;
    }}
    /* Sprint UX-119 AC3: selectboxes ganham altura mínima 44px e proteção
       contra glyphs cortados (`Mâs`, `2A26-04`, `Todos` apareciam mutilados
       pela altura justa). nowrap + overflow:hidden + text-overflow:ellipsis
       no VALOR SELECIONADO impedem quebra de palavra; o dropdown aberto
       usa overflow:visible herdado para não truncar opções. */
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stSelectbox"] div[role="combobox"] {{
        min-height: 44px;
        white-space: nowrap;
    }}
    [data-testid="stSelectbox"] div[role="combobox"] > div {{
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    /* Sprint UX-125 AC5: input de busca da sidebar ganha altura mínima
       44px (mesma altura dos selectboxes) para alinhamento visual e
       acessibilidade WCAG 2.1 (target tátil mínimo). Largura 100% do
       container já é default do Streamlit; reforçamos para evitar
       regressão em temas customizados. */
    [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {{
        min-height: 44px;
    }}
    /* Sprint UX-119 AC6: separador vertical roxo 2px entre sidebar e body.
       border-right adiciona linha visual sem mudar background (preservando
       regra UX-116 que define background-color e padding). Usar
       var(--color-destaque) (#BD93F9) garante coerência com a barra das
       tabs (UX-118) e com o token global de destaque. */
    [data-testid="stSidebar"] {{
        border-right: 2px solid var(--color-destaque);
    }}
    /* Sprint UX-119 AC7: header das páginas ganha respiro adicional
       (~48px) entre o título H1 e o conteúdo abaixo. Substitui o pedido
       informal "/n /n /n" do dono por margin-bottom estável no h1 dentro
       do main block container. Mantém PADDING_INTERNO (24px) original
       como padding do container e adiciona margin-bottom no título. */
    [data-testid="stMainBlockContainer"] h1 {{
        margin-bottom: {SPACING["xl"]}px !important;
    }}
    /* Sprint UX-119 AC10/11: container de chips e sugestões da página
       Busca Global (paginas/busca.py) usa flex-wrap + nowrap para garantir
       que nenhuma palavra quebra ao meio. Quando não couber numa linha, o
       botão inteiro vai para baixo. min-width 140px alinha visualmente os
       8 chips de tipo (Holerite/NF/DAS/Boleto/IRPF/Recibo/Comprovante/
       Contracheque) e as sugestões de autocomplete. As classes
       .ouroboros-chips-container e .ouroboros-sugestoes-container são
       adotadas em paginas/busca.py num passo posterior; por ora pintam
       qualquer container que receba a class. */
    .ouroboros-chips-container,
    .ouroboros-sugestoes-container {{
        display: flex;
        flex-wrap: wrap;
        gap: {SPACING["sm"]}px;
    }}
    .ouroboros-chips-container [data-testid="stButton"] > button,
    .ouroboros-sugestoes-container [data-testid="stButton"] > button {{
        flex: 0 0 auto;
        min-width: 140px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    /* Sprint UX-119 AC13: padronização global de stButton. Cards
       "DOCUMENTOS POR TIPO" da Catalogação e botões em geral ganham
       altura/largura mínima e proteção contra quebra de palavra. Quando
       o container não couber, o flex-wrap externo joga a linha inteira
       para baixo (regra do AC10/11). Aplicamos no seletor universal de
       stButton para cobrir todas as páginas de uma vez. */
    [data-testid="stButton"] > button {{
        min-height: 44px;
        min-width: 140px;
        white-space: nowrap;
    }}
    /* Sprint UX-118: logo da sidebar sai de 64x65 renderizado (apertado
       pela largura útil da sidebar) para ~120px com proporção da arte
       original (724x733px). Sprint UX-126 AC5: width/height/aspect-ratio
       agora carregam !important para vencer o atributo HTML width="64"
       que o caller (app.py) ainda passa por compatibilidade com versões
       legadas; o tamanho efetivo deve ser 120px independente do width
       atribuído ao <img>. */
    .ouroboros-logo-img {{
        width: 120px !important;
        height: auto !important;
        aspect-ratio: 724 / 733 !important;
        max-width: 120px !important;
        margin: 0 auto !important;
        display: block !important;
    }}
    /* Sprint UX-126 AC2: padding simétrico ao redor dos cards de tipos
       de documento. O container de st.columns ([data-testid=
       "stHorizontalBlock"]) recebe margin-top e margin-bottom iguais
       para que a distância entre o título "Documentos por tipo"
       (subtitulo_secao_html) e os cards seja igual à distância entre
       os cards e o divisor <hr> abaixo. */
    [data-testid="stHorizontalBlock"] {{
        margin-top: {SPACING["md"]}px;
        margin-bottom: {SPACING["md"]}px;
    }}
    [data-testid="stSidebar"] {{ background-color: {CORES["card_fundo"]}; }}
    /* Sprint UX-116: sidebar interna ganha padding 4 direções com PADDING_CHIP
       (16px). O retângulo interno [data-testid="stSidebar"] > div:first-child
       abriga logo + radio de cluster + filtros; sem padding explícito,
       controles colam na borda esquerda da sidebar. */
    [data-testid="stSidebar"] > div:first-child {{
        padding-top: {PADDING_CHIP}px !important;
        padding-right: {PADDING_CHIP}px !important;
        padding-bottom: {PADDING_CHIP}px !important;
        padding-left: {PADDING_CHIP}px !important;
    }}
    [data-testid="stSidebar"] h1 {{ color: {CORES["destaque"]}; }}
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {{ font-size: {FONTE_CORPO}px; }}
    [data-testid="stDownloadButton"] button {{
        background-color: {CORES["card_fundo"]};
        color: {CORES["texto"]};
        border: 1px solid {CORES["destaque"]};
        font-size: {FONTE_CORPO}px;
    }}
    [data-testid="stDownloadButton"] button:hover {{
        background-color: {CORES["destaque"]};
        color: {CORES["fundo"]};
    }}
    h1 {{ font-size: {FONTE_HERO}px !important; font-weight: 700 !important; }}
    h2 {{ font-size: {FONTE_TITULO}px !important; font-weight: 700 !important; }}
    h3 {{ font-size: {FONTE_SUBTITULO}px !important; font-weight: 600 !important; }}
    p, li, span, div {{ font-size: {FONTE_CORPO}px; }}
    .stTabs [data-baseweb="tab-list"],
    .stTabs [data-baseweb="tab-list"] > div,
    .stTabs > div:first-child {{
        gap: {SPACING["sm"]}px;
        background-color: {CORES["card_fundo"]};
        border-radius: 8px;
        min-height: 60px !important;
        height: auto !important;
        overflow: visible !important;
        overflow-y: visible !important;
        overflow-x: auto !important;
    }}
    /* Sprint UX-118: barra de tabs fica fixa no topo durante scroll com
       linha 2px na cor destaque (#BD93F9) abaixo, marcando o limite entre
       navegação e conteúdo. position: sticky + top: 0 + z-index alto
       garantem que tabs não sejam cobertas pelo conteúdo ao rolar. Aplicado
       só ao seletor pai (tab-list) — não estendemos para os filhos > div
       para evitar duplicar a borda. */
    .stTabs [data-baseweb="tab-list"] {{
        position: sticky;
        top: 0;
        z-index: 10;
        border-bottom: 2px solid var(--color-destaque);
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {CORES["texto_sec"]} !important;
        font-size: {FONTE_CORPO}px !important;
        padding: {SPACING["md"]}px {SPACING["md"] + 4}px !important;
        height: auto !important;
        min-height: 48px !important;
        white-space: nowrap !important;
        overflow: visible !important;
        display: flex !important;
        align-items: center !important;
    }}
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] div {{
        color: inherit !important;
        font-size: {FONTE_CORPO}px !important;
        overflow: visible !important;
        line-height: 1.4 !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {CORES["texto"]} !important;
        font-weight: bold !important;
        border-bottom: 3px solid {CORES["destaque"]} !important;
    }}
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] div {{
        color: {CORES["texto"]} !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {CORES["texto"]} !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: transparent !important;
        display: none !important;
    }}
    .element-container {{ margin-bottom: {SPACING["md"]}px; }}
    [data-testid="stHorizontalBlock"] {{ gap: {SPACING["md"]}px; }}

    /* P2.2 2026-04-23: alertas do Streamlit alinhados ao tema Dracula.
       Default usa amarelo pálido que destoa do tema escuro. */
    [data-testid="stAlert"] {{
        background-color: {CORES["card_fundo"]} !important;
        color: {CORES["texto"]} !important;
        border-left: 4px solid {CORES["destaque"]} !important;
        border-radius: 6px;
    }}
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] span,
    [data-testid="stAlert"] div {{
        color: {CORES["texto"]} !important;
    }}

    /* --- Sprint UX-112: bordas e padding universais em inputs/selects --- */
    /* Borda padrão 1px texto_sec; foco eleva para borda-ativa-px destaque.
       Padding-chip aplicado em controles compactos. */
    [data-testid="stTextInput"] > div > div,
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div,
    [data-testid="stTextArea"] > div > div,
    [data-testid="stNumberInput"] > div > div,
    [data-testid="stDateInput"] > div > div {{
        border: 1px solid {CORES["texto_sec"]} !important;
        border-radius: var(--borda-raio) !important;
        background-color: {CORES["card_fundo"]} !important;
        padding: var(--spacing-xs) var(--padding-chip) !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    [data-testid="stTextInput"]:focus-within > div > div,
    [data-testid="stSelectbox"]:focus-within > div > div,
    [data-testid="stMultiSelect"]:focus-within > div > div,
    [data-testid="stTextArea"]:focus-within > div > div,
    [data-testid="stNumberInput"]:focus-within > div > div,
    [data-testid="stDateInput"]:focus-within > div > div {{
        border: var(--borda-ativa-px) solid {CORES["destaque"]} !important;
        box-shadow: 0 0 0 1px {CORES["destaque"]}33 !important;
    }}

    /* Expanders ganham borda visível e padding interno coerente. */
    [data-testid="stExpander"] {{
        border: 1px solid {CORES["texto_sec"]} !important;
        border-radius: var(--borda-raio) !important;
        background-color: {CORES["card_fundo"]} !important;
        margin: var(--spacing-sm) 0;
    }}
    [data-testid="stExpander"] details > summary {{
        padding: var(--spacing-sm) var(--padding-chip) !important;
    }}
    [data-testid="stExpander"] details[open] > div:last-child,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        padding: var(--padding-chip) var(--padding-interno) !important;
    }}

    /* Corpo das tabs (painel abaixo da barra) ganha padding-top para evitar
       conteúdo colado no separador. */
    .stTabs [data-baseweb="tab-panel"] {{
        padding-top: var(--padding-chip) !important;
    }}

    /* --- Grid responsivo de KPI cards (Sprint 62) ------------------------ */
    /* Grid fluido com minmax: 3 colunas em telas largas, 2 em médias e 1 em
       estreitas. Substitui `st.columns(3)` rígido quando renderizado como
       bloco HTML custom via kpi_grid_html(). */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: {SPACING["md"]}px;
        width: 100%;
    }}
    .kpi-grid > .kpi-card {{
        min-width: 0;  /* permite shrink abaixo do conteúdo */
    }}
    .kpi-card .kpi-label {{
        color: {CORES["texto_sec"]};
        font-size: {FLUID_LABEL_KPI};
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .kpi-card .kpi-valor {{
        font-size: {FLUID_VALOR_KPI};
        font-weight: bold;
        margin: {SPACING["xs"]}px 0 0 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    @media (max-width: {BREAKPOINT_COMPACTO}px) {{
        .kpi-grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
        /* Streamlit columns fallback: quando visao_geral ainda usa st.columns(3),
           força cada coluna a 50% em viewports compactos. */
        [data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
        }}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
            flex: 1 1 calc(50% - {SPACING["md"]}px) !important;
            min-width: calc(50% - {SPACING["md"]}px) !important;
        }}
    }}
    @media (max-width: {BREAKPOINT_MINIMO}px) {{
        .kpi-grid {{
            grid-template-columns: 1fr;
        }}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }}
        /* Sprint UX-127 AC1: input de busca da sidebar não corta em viewport
           estreito. Em telas <=700px o container interno e o <input> ganham
           width: 100% + box-sizing: border-box + overflow: visible. Sem
           isso, o conteúdo do <input> some quando a sidebar encolhe abaixo
           do default do Streamlit (~280px) e o usuário não vê o que digita.
           Combina com a regra UX-125 AC5 (min-height: 44px) que já vive em
           outro bloco do css_global. */
        [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {{
            width: 100% !important;
            overflow: visible !important;
        }}
        [data-testid="stSidebar"] [data-testid="stTextInput"] input {{
            width: 100% !important;
            box-sizing: border-box !important;
        }}
    }}

    /* --- Gráfico: título não sobrepõe legenda (Sprint 62) --------------- */
    /* Plotly em viewport estreito cola a legenda horizontal no topo do
       gráfico. Garante espaçamento mínimo entre título e legenda. */
    .js-plotly-plot .plotly .g-gtitle {{
        margin-bottom: {SPACING["md"]}px;
    }}

    /* --- Sprint 92c: classes utilitarias de layout ---------------------- */
    /* Substitui inline <div style="display: flex; ..."> pontuais nas paginas
       pelo menor conjunto possivel de classes reutilizaveis. CSS vars acima
       em :root garantem coerencia de spacing e cor. */
    .ouroboros-row-between {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: var(--spacing-sm);
    }}
    .ouroboros-row-flex {{
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-sm);
        align-items: center;
    }}
    .ouroboros-row-flex-xs {{
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-xs);
    }}
    .ouroboros-label-icon {{
        display: flex;
        align-items: center;
        gap: var(--spacing-xs);
        color: var(--color-destaque);
        font-size: var(--font-corpo);
        font-weight: 600;
        margin-bottom: var(--spacing-xs);
        /* Sprint UX-115: contrato explícito de alinhamento à esquerda --
           label "Busca global" deve iniciar em x=0 do block-container,
           coincidindo com a borda esquerda do input principal. */
        margin-left: 0;
        padding-left: 0;
        justify-content: flex-start;
    }}
    .ouroboros-row-resumo-busca {{
        margin: var(--spacing-md) 0;
    }}
    .ouroboros-card-hero-busca {{
        background-color: var(--color-card-fundo);
        border-radius: 10px;
        padding: var(--spacing-md);
        margin-bottom: var(--spacing-sm);
        border-left: 4px solid var(--color-destaque);
    }}
    .ouroboros-aliases-line {{
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-xs);
    }}
    .ouroboros-ritmo-card {{
        padding: var(--spacing-xs) 0;
    }}
    .ouroboros-timeline-container {{
        background-color: var(--color-card-fundo);
        border-radius: 8px;
        padding: var(--spacing-lg);
    }}
    .ouroboros-timeline-tronco {{
        border-left: 2px solid var(--color-card-fundo);
        padding-left: var(--spacing-lg);
        margin-left: var(--spacing-sm);
    }}
    .ouroboros-chips-tipos {{
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-xs);
        margin-top: var(--spacing-sm);
    }}
    .ouroboros-moc-preview {{
        background-color: var(--color-card-fundo);
        border-radius: 10px;
        padding: var(--spacing-md) calc(var(--spacing-md) + 4px);
        margin-top: var(--spacing-sm);
        max-height: 520px;
        overflow-y: auto;
        font-family: 'JetBrains Mono', monospace;
        font-size: var(--font-label);
        line-height: 1.6;
        color: var(--color-texto);
    }}
    .ouroboros-timeline-evento {{
        position: relative;
        margin-bottom: var(--spacing-lg);
    }}
    </style>
    """


# "Forma é a expressão visível da função." -- Louis Sullivan
