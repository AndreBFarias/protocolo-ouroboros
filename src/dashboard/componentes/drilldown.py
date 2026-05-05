"""Drill-down interativo via clique em gráfico Plotly — Sprint 73 (ADR-19).

Helper único `aplicar_drilldown(fig, campo_customdata, tab_destino, key_grafico)`
que renderiza o `fig` com `st.plotly_chart(..., on_select="rerun")`, captura o
ponto clicado via `customdata`, seta `st.query_params` e dispara exatamente UM
`st.rerun()`. O debounce é feito por hash em `st.session_state[f"{key}_last_click_hash"]`
para impedir loop infinito (rerun re-invoca on_select com o mesmo estado).

Leitor auxiliar `ler_filtros_da_url()` é chamado por `app.py` no início do
ciclo de renderização para popular `st.session_state` a partir de URLs
compartilháveis como `?tab=Extrato&categoria=Farmácia`.

Requisitos:
  - Streamlit >= 1.31 (on_select nativo).
  - Traces do Plotly com `customdata` populado pelo caller.
  - `key_grafico` único por gráfico (obrigatório para o `on_select` funcionar).
"""

from __future__ import annotations

from typing import Any

# Lista fechada de campos que o drill-down reconhece como filtros válidos
# (espelha as colunas relevantes da aba Extrato).
#
# Sprint 92b (ADR-22): "cluster" entrou na whitelist como campo de navegação
# de primeiro nível (cluster -> aba). Continua sendo tratado como filtro no
# sentido de que é lido da URL e gravado em session_state, mas semanticamente
# é nivel de hierarquia, não filtro de coluna.
CAMPOS_FILTRO_RECONHECIDOS: frozenset[str] = frozenset(
    {
        "mes",
        "mes_ref",
        "categoria",
        "classificacao",
        "fornecedor",
        "banco",
        "banco_origem",
        "local",
        "forma",
        "forma_pagamento",
        "cluster",
    }
)

# Chaves canônicas que o Extrato usa para ler filtros vindos do drill-down.
CHAVE_SESSION_ABA_ATIVA: str = "aba_ativa_requerida"

# Sprint 92b (ADR-22): mapa canônico aba -> cluster. Permite que URL antiga
# no formato ?tab=Extrato (sem parâmetro cluster) seja interpretada pelo
# leitor inferindo o cluster implícito. URL nova ?cluster=Finanças&tab=Extrato
# explicita o cluster e pula a inferência.
#
# Sprint UX-125: tabs do cluster Home foram renomeadas para espelhar os
# clusters-irmãos (Visão Geral / Finanças / Documentos / Análise / Metas) -
# sem o sufixo "hoje" repetitivo. Como "Finanças", "Documentos", "Análise"
# e "Metas" também são nomes de clusters próprios, apenas o cluster
# canônico fica registrado neste mapa (chaves únicas em dict). As tabs
# homônimas dentro do Home são acessadas exclusivamente com cluster
# explícito (?cluster=Home&tab=Finanças). Sem cluster na URL, ?tab=X infere
# o cluster próprio (preserva semântica das URLs anteriores).
MAPA_ABA_PARA_CLUSTER: dict[str, str] = {
    "Visão Geral": "Home",
    "Extrato": "Finanças",
    "Contas": "Finanças",
    "Pagamentos": "Finanças",
    "Projeções": "Finanças",
    "Catalogação": "Documentos",
    "Completude": "Documentos",
    "Busca Global": "Documentos",
    "Grafo + Obsidian": "Documentos",
    "Revisor": "Documentos",
    "Validação por Arquivo": "Documentos",
    "Categorias": "Análise",
    "Análise": "Análise",
    "IRPF": "Análise",
    "Metas": "Metas",
    # Sprint UX-RD-03: abas dos 3 clusters novos. As páginas ainda não
    # existem (UX-RD-15 / UX-RD-16+ / UX-RD-05 implementam), mas a entrada
    # no mapa preserva o invariante N-para-N entre ABAS_POR_CLUSTER e
    # MAPA_ABA_PARA_CLUSTER -- sem isso, navegar via deep-link
    # ?tab=Inbox falharia silenciosamente.
    "Inbox": "Inbox",
    "Hoje": "Bem-estar",
    "Humor": "Bem-estar",
    "Diário emocional": "Bem-estar",
    "Skills D7": "Sistema",
    # Sprint UX-RD-05: aba "Styleguide" entra no cluster Sistema.
    # Mantém invariante N-para-N com ABAS_POR_CLUSTER["Sistema"].
    "Styleguide": "Sistema",
}

# Sprint UX-125: tabs do cluster Home com nome igual a cluster próprio.
# Lista documenta a homonímia consciente; usado em invariantes de teste
# para distinguir tabs do Home (resolvidas só com cluster explícito) das
# tabs canônicas (resolvidas pelo MAPA_ABA_PARA_CLUSTER).
ABAS_HOME_HOMONIMAS: frozenset[str] = frozenset({"Finanças", "Documentos", "Análise", "Metas"})

# Clusters válidos (ordem canônica da sidebar). Usado por testes e por validação
# defensiva em app.py (rejeita cluster fora do conjunto ao ler da URL).
#
# Sprint UX-121: cluster "Hoje" renomeado para "Home" (termo padrão web/apps;
# "Hoje" sugeria período temporal, criando ambiguidade no ponto de entrada).
# Sprint UX-125: cluster "Dinheiro" renomeado para "Finanças" (termo mais
# profissional; alias backward-compat preserva URLs antigas).
#
# Sprint UX-RD-03: cluster set estendido de 5 para 8 áreas (Inbox, Bem-estar,
# Sistema entram). Inbox é ponto de entrada da fila de novos arquivos
# (UX-RD-15 implementa); Bem-estar agrupa as 12 telas pessoais não-financeiras
# do redesign (UX-RD-16+ implementa); Sistema reúne Skills D7, Styleguide e
# Índice (UX-RD-05 implementa). Ordem aqui espelha 1:1 a ordem da sidebar
# definida em ``novo-mockup/_shared/shell.js`` (CLUSTERS_OUROBOROS). Páginas
# desses 3 clusters ainda não existem em ``paginas/``; o dispatcher em
# ``app.main()`` renderiza fallback graceful (st.info) que aponta para a
# sprint que vai implementar.
CLUSTERS_VALIDOS: tuple[str, ...] = (
    "Inbox",
    "Home",
    "Finanças",
    "Documentos",
    "Análise",
    "Metas",
    "Bem-estar",
    "Sistema",
)

# Sprint UX-121: aliases backward-compat para query_params. Permite que URLs
# antigas no formato ?cluster=Hoje continuem resolvendo para o novo nome
# canônico "Home" sem quebrar bookmarks ou links externos. Aplicado em
# `ler_filtros_da_url` antes da validação contra CLUSTERS_VALIDOS.
#
# Sprint UX-125: alias adicional ?cluster=Dinheiro -> "Finanças".
CLUSTER_ALIASES: dict[str, str] = {"Hoje": "Home", "Dinheiro": "Finanças"}

# Chave canônica em session_state para o cluster ativo. Namespace próprio,
# não colide com filtro_* (drill-down), avancado_* (filtros manuais Extrato)
# ou seletor_* (selectbox da sidebar).
CHAVE_SESSION_CLUSTER_ATIVO: str = "cluster_ativo"


def _session_state() -> Any:
    """Devolve `st.session_state` quando streamlit está disponível."""
    import streamlit as st

    return st.session_state


def _extrair_valor_do_ponto(ponto: dict) -> Any:
    """Extrai o valor canônico do ponto clicado no Plotly."""
    valor = ponto.get("customdata")
    if valor is None:
        valor = ponto.get("label")
    if valor is None:
        valor = ponto.get("x")
    return valor


def aplicar_drilldown(
    fig: Any,
    campo_customdata: str,
    tab_destino: str,
    key_grafico: str,
) -> None:
    """Renderiza `fig` com drill-down e navega para aba filtrada ao clicar.

    Uso:

        fig = px.treemap(df, path=["classificacao", "categoria"], values="valor")
        fig.update_traces(customdata=df["categoria"])
        aplicar_drilldown(fig, "categoria", "Extrato", key_grafico="treemap_categ")

    - `campo_customdata`: nome do filtro que será gravado em `query_params`
      (ex: "categoria" ou "mes_ref").
    - `tab_destino`: nome da aba para onde navegar (ex: "Extrato").
    - `key_grafico`: chave única do gráfico; sem ela `on_select` não funciona
      no Streamlit 1.31+.
    """
    if not key_grafico:
        raise ValueError("key_grafico é obrigatório para on_select funcionar")
    import streamlit as st

    fig.update_layout(clickmode="event+select")
    resultado = st.plotly_chart(
        fig,
        use_container_width=True,
        key=key_grafico,
        on_select="rerun",
    )

    if not isinstance(resultado, dict):
        return
    pontos = resultado.get("selection", {}).get("points", []) or []
    if not pontos:
        return

    ponto = pontos[0]
    valor = _extrair_valor_do_ponto(ponto)
    if valor is None:
        return
    valor_str = str(valor)

    click_hash = f"{campo_customdata}={valor_str}|tab={tab_destino}"
    chave_debounce = f"{key_grafico}_last_click_hash"

    estado = _session_state()
    if estado.get(chave_debounce) == click_hash:
        return  # já processado: evita loop de rerun
    estado[chave_debounce] = click_hash

    # Normaliza campo: "mes" e "mes_ref" são intercambiáveis; idem "banco"/"banco_origem"
    # etc. O Extrato decide qual coluna usar ao aplicar o filtro.
    st.query_params[campo_customdata] = valor_str
    st.query_params["tab"] = tab_destino
    st.rerun()


def ler_filtros_da_url() -> None:
    """Copia `st.query_params` para `st.session_state` para filtros conhecidos.

    Deve ser chamado no início de `app.py` antes de renderizar abas. Idempotente:
    se o param não existe na URL, a session_state não é alterada.

    Sprint 92b (ADR-22): além dos filtros de coluna, o leitor agora resolve
    o cluster ativo com a seguinte ordem de precedência:

    1. `?cluster=<X>` na URL (explícito) e X em CLUSTERS_VALIDOS -> usa X.
    2. `?tab=<Y>` na URL e Y em MAPA_ABA_PARA_CLUSTER -> infere cluster.
    3. Nenhum dos dois -> session_state[cluster_ativo] fica intocado (default
       é definido pelo radio em app.py, tipicamente "Home").

    Sprint UX-121: aplica `CLUSTER_ALIASES` antes da validação contra
    CLUSTERS_VALIDOS. URLs antigas (?cluster=Hoje) resolvem para "Home"
    transparentemente, preservando bookmarks e links externos.
    """
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        return

    qp = st.query_params
    # Converte `st.query_params` num dict simples para evitar surpresas com
    # streamlit retornando listas para keys duplicadas.
    for campo in CAMPOS_FILTRO_RECONHECIDOS:
        if campo in qp:
            valor = qp[campo]
            if isinstance(valor, list):
                valor = valor[0] if valor else ""
            st.session_state[f"filtro_{campo}"] = str(valor)

    if "tab" in qp:
        valor_tab = qp["tab"]
        if isinstance(valor_tab, list):
            valor_tab = valor_tab[0] if valor_tab else ""
        st.session_state[CHAVE_SESSION_ABA_ATIVA] = str(valor_tab)

    # Sprint 92b: resolve cluster ativo (explícito ou inferido pela aba).
    cluster_explicito: str = ""
    if "cluster" in qp:
        valor_cluster = qp["cluster"]
        if isinstance(valor_cluster, list):
            valor_cluster = valor_cluster[0] if valor_cluster else ""
        cluster_explicito = str(valor_cluster)

    # Sprint UX-121: resolve aliases backward-compat antes de validar.
    cluster_explicito = CLUSTER_ALIASES.get(cluster_explicito, cluster_explicito)

    if cluster_explicito and cluster_explicito in CLUSTERS_VALIDOS:
        st.session_state[CHAVE_SESSION_CLUSTER_ATIVO] = cluster_explicito
    elif "tab" in qp:
        aba = st.session_state.get(CHAVE_SESSION_ABA_ATIVA, "")
        cluster_inferido = MAPA_ABA_PARA_CLUSTER.get(aba, "")
        if cluster_inferido:
            st.session_state[CHAVE_SESSION_CLUSTER_ATIVO] = cluster_inferido


def gerar_html_ativar_aba(nome_aba: str, abas_do_cluster: list[str]) -> str:
    """Gera HTML com JavaScript que ativa programaticamente a aba ``nome_aba``.

    Sprint 100: Streamlit ``st.tabs(...)`` não expõe API para ativar tab por
    nome -- precisa simular click no DOM (ARMADILHAS.md item 11). O HTML
    retornado, quando injetado via ``st.components.v1.html(html, height=0)``,
    faz duas coisas no browser:

    1. **Click programático**: localiza a tab cujo índice no DOM
       (``[role="tab"]``) corresponde à posição de ``nome_aba`` na lista
       ``abas_do_cluster`` e dispara ``.click()``. Usa ``setTimeout`` curto
       para esperar o Streamlit terminar de montar a tab bar; reagenda 1 vez
       se o DOM ainda não tem tabs suficientes; desiste silenciosamente
       depois disso (graceful degradation, sem crash visual).
    2. **Write-back de URL**: instala listener em cada tab; quando usuário
       clica manualmente, atualiza ``?tab=<NomeClicado>`` via
       ``history.replaceState`` (não empilha histórico inútil; o browser
       back continua semântico). Acceptance #3 da Sprint 100.

    Args:
        nome_aba: Nome textual da aba a ativar (ex: "Busca Global"). Se
            vazia ou ausente em ``abas_do_cluster``, devolve string vazia
            (no-op).
        abas_do_cluster: Lista ordenada das abas no cluster atual, na MESMA
            ordem passada para ``st.tabs(...)``. Ordem importa: JS navega
            por índice no DOM.

    Returns:
        HTML pronto para ``st.components.v1.html``. String vazia se nada a
        fazer.
    """
    if not nome_aba or nome_aba not in abas_do_cluster:
        return ""
    indice_alvo = abas_do_cluster.index(nome_aba)
    # Mapa textual nome -> índice, sem dependência de json (escapamos aspas
    # com cuidado; nomes de abas do projeto não têm aspas internas).
    pares = ", ".join(f'"{aba}": {i}' for i, aba in enumerate(abas_do_cluster))
    return f"""
<script>
(function() {{
  const indiceAlvo = {indice_alvo};
  const mapaAbas = {{{pares}}};

  function tryAtivar(tentativa) {{
    const docTopo = window.parent && window.parent.document
      ? window.parent.document
      : document;
    const tabs = docTopo.querySelectorAll('[role="tab"]');
    if (!tabs || tabs.length <= indiceAlvo) {{
      // Streamlit pode demorar para hidratar (páginas pesadas como
      // Catalogação carregam dados antes do tab bar montar). Tentamos até
      // 30x com 300ms entre tentativas (~9s total) -- balanço entre
      // velocidade percebida e robustez. Após isso, desistimos
      // silenciosamente sem crash visual.
      if (tentativa < 30) {{
        setTimeout(() => tryAtivar(tentativa + 1), 300);
      }}
      return;
    }}
    const jaAtivo = tabs[indiceAlvo].getAttribute('aria-selected') === 'true';
    if (!jaAtivo) {{
      tabs[indiceAlvo].click();
    }}
    instalarWriteBack(docTopo, tabs);
  }}

  function instalarWriteBack(docTopo, tabs) {{
    tabs.forEach((tab) => {{
      if (tab.dataset.ouroborosListener === '1') return;
      tab.dataset.ouroborosListener = '1';
      tab.addEventListener('click', () => {{
        const texto = (tab.innerText || '').trim();
        if (texto in mapaAbas) {{
          try {{
            const url = new URL(window.parent.location.href);
            url.searchParams.set('tab', texto);
            window.parent.history.replaceState({{}}, '', url.toString());
          }} catch (e) {{
            /* graceful: cross-origin ou history bloqueado */
          }}
        }}
      }});
    }});
  }}

  setTimeout(() => tryAtivar(0), 100);
}})();
</script>
"""


def filtros_ativos_do_session_state() -> dict[str, str]:
    """Extrai filtros vindos de drill-down do session_state (Sprint 73).

    Usado pela aba Extrato para aplicar filtros e renderizar breadcrumb.
    Devolve dict apenas com chaves com valor não-vazio.
    """
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        return {}

    resultado: dict[str, str] = {}
    for campo in CAMPOS_FILTRO_RECONHECIDOS:
        chave = f"filtro_{campo}"
        if chave in st.session_state and st.session_state[chave]:
            resultado[campo] = str(st.session_state[chave])
    return resultado


def limpar_filtro(campo: str) -> None:
    """Remove um filtro específico do session_state e do query_params."""
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        return

    chave_sessao = f"filtro_{campo}"
    if chave_sessao in st.session_state:
        del st.session_state[chave_sessao]
    if campo in st.query_params:
        del st.query_params[campo]


# "Clicar num número e ir até a transação é o mínimo." -- ditado popular do projeto, 2026-04-21
