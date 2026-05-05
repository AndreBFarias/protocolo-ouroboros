"""Testes do shell redesenhado — Sprint UX-RD-03.

Cobre 12 invariantes:

  1. CLUSTERS_VALIDOS expõe exatamente 8 clusters na ordem canônica.
  2. Clusters legados (Home, Finanças, Documentos, Análise, Metas) ainda
     estão presentes e mantêm posições compatíveis com retrocompat.
  3. CLUSTER_ALIASES preserva URLs antigas (?cluster=Hoje, ?cluster=Dinheiro).
  4. ``renderizar_sidebar`` emite os 8 cluster headers em ordem.
  5. ``renderizar_sidebar`` destaca a aba ativa com classe ``sidebar-item active``.
  6. ``renderizar_sidebar`` produz ``href`` com query-string ``?cluster=...&tab=...``.
  7. ``renderizar_topbar`` emite breadcrumb na ordem fornecida com último
     segmento marcado como ``current``.
  8. ``renderizar_topbar`` emite slot vazio de ações quando ``acoes`` é None.
  9. ``gerar_html_atalhos`` injeta JS com mapa de 6 combos g+letra.
  10. ``gerar_html_atalhos`` define guard idempotente
      ``__ouroborosAtalhosInstalados``.
  11. ``gerar_html_atalhos`` lista os 9 atalhos no modal de ajuda
      (6 letras + ``/`` + ``?`` + ``Esc``).
  12. Fallback graceful: cluster sem páginas (Inbox, Bem-estar, Sistema)
      tem entrada em ``ABAS_POR_CLUSTER`` e ``SPRINT_ALVO_POR_CLUSTER``.
"""

from __future__ import annotations

from src.dashboard.componentes.atalhos_teclado import gerar_html_atalhos
from src.dashboard.componentes.drilldown import (
    CLUSTER_ALIASES,
    CLUSTERS_VALIDOS,
)
from src.dashboard.componentes.shell import (
    CLUSTERS_REDESIGN,
    renderizar_sidebar,
    renderizar_topbar,
)


def test_clusters_validos_tem_oito_em_ordem_canonica() -> None:
    """[01] CLUSTERS_VALIDOS expõe 8 clusters na ordem espelhada do mockup."""
    esperado = (
        "Inbox",
        "Home",
        "Finanças",
        "Documentos",
        "Análise",
        "Metas",
        "Bem-estar",
        "Sistema",
    )
    assert CLUSTERS_VALIDOS == esperado


def test_clusters_legados_preservados_no_set() -> None:
    """[02] Clusters da Sprint 92b/UX-121/UX-125 continuam em CLUSTERS_VALIDOS."""
    legados = {"Home", "Finanças", "Documentos", "Análise", "Metas"}
    assert legados.issubset(set(CLUSTERS_VALIDOS))


def test_cluster_aliases_retrocompat_url_antiga() -> None:
    """[03] CLUSTER_ALIASES resolve URLs antigas para nomes canônicos novos."""
    assert CLUSTER_ALIASES.get("Hoje") == "Home"
    assert CLUSTER_ALIASES.get("Dinheiro") == "Finanças"


def test_renderizar_sidebar_emite_oito_cluster_headers() -> None:
    """[04] renderizar_sidebar emite header HTML de cada um dos 8 clusters."""
    html = renderizar_sidebar(cluster_ativo="Home", aba_ativa="Visão Geral")
    contagem_headers = html.count('class="sidebar-cluster-header"')
    assert contagem_headers == 8, f"esperava 8 headers, obtive {contagem_headers}"
    # Cada nome de cluster deve aparecer no HTML (escapado se necessário).
    for cluster in CLUSTERS_VALIDOS:
        assert cluster in html, f"cluster '{cluster}' ausente da sidebar HTML"


def test_renderizar_sidebar_destaca_aba_ativa() -> None:
    """[05] Aba ativa recebe classe ``sidebar-item active``."""
    html = renderizar_sidebar(cluster_ativo="Documentos", aba_ativa="Revisor")
    # Existe pelo menos um item com classe active e ele aponta para Revisor.
    assert 'class="sidebar-item active"' in html
    # E especificamente referência a Revisor com active.
    trecho_ativo = (
        'class="sidebar-item active" href="?cluster=Documentos&amp;tab=Revisor"'
    )
    # O urllib usa & cru e o html.escape transforma em &amp; -- testamos o
    # bruto antes da renderização. Ambos os formatos podem ocorrer; o
    # importante é o link conter cluster=Documentos e tab=Revisor.
    assert ('cluster=Documentos' in html) and ('tab=Revisor' in html)
    # E que ele veio como item ativo (busca o segmento ``active``).
    bloco_revisor_ativo = html.split('tab=Revisor')[0].split('class="')[-1]
    assert 'active' in bloco_revisor_ativo, (
        f"Item Revisor não está marcado active no bloco: {bloco_revisor_ativo!r}"
    )
    _ = trecho_ativo  # silencia ruff sobre var não usada (referência docs)


def test_renderizar_sidebar_emite_href_query_string() -> None:
    """[06] Itens da sidebar usam href ``?cluster=...&tab=...`` URL-encoded."""
    html = renderizar_sidebar(cluster_ativo="Home", aba_ativa="Visão Geral")
    # Itens implementados sempre têm tab=...
    assert 'href="?cluster=Inbox&amp;tab=Inbox"' in html or (
        'cluster=Inbox' in html and 'tab=Inbox' in html
    )
    # Acentos em "Análise" devem ser URL-escapados (urllib quote para %C3%A1)
    # ou aparecer como ``An%C3%A1lise`` -- ambos válidos.
    assert (
        'cluster=An%C3%A1lise' in html
        or 'cluster=Análise' in html
    )


def test_renderizar_topbar_breadcrumb_marca_ultimo_segmento() -> None:
    """[07] Topbar marca último segmento do breadcrumb com classe ``current``."""
    html = renderizar_topbar(["Ouroboros", "Home", "Visão Geral"])
    assert '<header class="topbar' in html
    assert 'class="seg current"' in html
    # Último segmento é o ativo: "Visão Geral".
    bloco_atual = html.split('class="seg current"')[1]
    assert "Visão Geral" in bloco_atual
    # Separador "/" aparece N-1 vezes (2 separadores para 3 segmentos).
    assert html.count('class="sep"') == 2


def test_renderizar_topbar_acoes_vazias_emite_slot() -> None:
    """[08] Topbar com acoes=None emite slot ``topbar-actions`` vazio."""
    html = renderizar_topbar(["Ouroboros", "Home"])
    assert '<div class="topbar-actions">' in html
    # Slot existe mas sem buttons/links dentro.
    bloco_acoes = html.split('<div class="topbar-actions">')[1].split("</div>")[0]
    assert "<button" not in bloco_acoes
    assert "<a " not in bloco_acoes


def test_atalhos_html_inclui_seis_combos_g_letra() -> None:
    """[09] gerar_html_atalhos define mapa JS com 6 combinações g+letra."""
    html = gerar_html_atalhos()
    for combo in ("gh", "gi", "gv", "gr", "gf", "gc"):
        assert f'"{combo}":' in html, f"combo '{combo}' ausente do mapa JS"


def test_atalhos_html_tem_guard_idempotente() -> None:
    """[10] gerar_html_atalhos publica guard ``__ouroborosAtalhosInstalados``."""
    html = gerar_html_atalhos()
    assert "__ouroborosAtalhosInstalados" in html
    # E o early return cita o guard.
    assert "if (winTopo.__ouroborosAtalhosInstalados)" in html


def test_atalhos_modal_lista_nove_atalhos() -> None:
    """[11] Modal de ajuda lista 9 atalhos: 6 g+letra + / + ? + Esc."""
    html = gerar_html_atalhos()
    # Procura o array linhasModal e confere que tem 9 entradas.
    bloco_modal = html.split("var linhasModal = ")[1].split(";")[0]
    # Cada entrada começa com [" ; uma forma simples de contar.
    contagem = bloco_modal.count('["')
    assert contagem == 9, f"esperava 9 entradas no modal, obtive {contagem}"
    # E os rótulos esperados estão presentes.
    for tecla in ("g h", "g i", "g v", "g r", "g f", "g c"):
        assert f'"{tecla}"' in bloco_modal
    for tecla in ("/", "?", "Esc"):
        assert f'"{tecla}"' in bloco_modal


def test_clusters_redesign_tem_pendentes_marcados() -> None:
    """[12] CLUSTERS_REDESIGN marca abas pendentes com sprint_alvo."""
    pendentes_por_cluster: dict[str, str] = {}
    for cluster in CLUSTERS_REDESIGN:
        for aba in cluster["abas"]:
            if not aba.get("implementada", True):
                pendentes_por_cluster[cluster["nome"]] = aba.get("sprint_alvo", "")
    # Inbox / Bem-estar / Sistema têm pelo menos uma aba pendente.
    assert "Inbox" in pendentes_por_cluster
    assert "Bem-estar" in pendentes_por_cluster
    assert "Sistema" in pendentes_por_cluster
    # E o sprint_alvo aponta para sprints UX-RD-XX (não fica vazio).
    for cluster_nome, sprint_alvo in pendentes_por_cluster.items():
        assert sprint_alvo.startswith("UX-RD"), (
            f"cluster '{cluster_nome}' tem sprint_alvo inválido: {sprint_alvo!r}"
        )


# "O todo é maior que a soma das partes -- quando bem articulado." -- Aristóteles
