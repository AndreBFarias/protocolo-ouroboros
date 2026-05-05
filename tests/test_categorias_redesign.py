"""Testes UX-RD-12 — Categorias reescrita.

Cobre as funções puras introduzidas pela reescrita:

* árvore agregada por classificação + categoria;
* KPIs do topo (saída, cobertura, maior família, não-classificadas);
* paleta WCAG-AA validada contra fundo dark `#0e0f15`;
* leitura de regras YAML (cache LRU);
* contagem de hits por regra dentro do recorte;
* HTML da árvore com `details` expansível e classes do mockup;
* HTML do painel de regras com categoria-filtro e fallback global;
* invariante de viewport (renderização HTML não excede 1200 caracteres por
  linha: minificação ativa para evitar bloco `<pre>` do CommonMark).
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.dashboard.paginas import categorias as pagina
from src.dashboard.tema import CORES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def df_categorias() -> pd.DataFrame:
    """DataFrame com 3 categorias × 2 classificações × várias linhas."""
    return pd.DataFrame(
        [
            {
                "data": pd.Timestamp("2026-04-02"),
                "valor": -1280.00,
                "local": "SUPERLOGICA aluguel",
                "categoria": "Aluguel",
                "classificacao": "Obrigatório",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
            },
            {
                "data": pd.Timestamp("2026-04-04"),
                "valor": -127.40,
                "local": "IFD*Sushi Yamamoto",
                "categoria": "Delivery",
                "classificacao": "Questionável",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
            },
            {
                "data": pd.Timestamp("2026-04-05"),
                "valor": -94.80,
                "local": "UBER trip",
                "categoria": "Transporte",
                "classificacao": "Questionável",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
            },
            {
                "data": pd.Timestamp("2026-04-06"),
                "valor": -54.30,
                "local": "IFOOD lanche",
                "categoria": "Delivery",
                "classificacao": "Questionável",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
            },
            {
                "data": pd.Timestamp("2026-04-07"),
                "valor": -432.10,
                "local": "??? nada bate",
                "categoria": "Outros",
                "classificacao": "Questionável",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
            },
        ]
    )


# ---------------------------------------------------------------------------
# 1. Paleta WCAG-AA
# ---------------------------------------------------------------------------
def test_treemap_paleta_wcag_aa_minimo_45() -> None:
    """Toda cor da paleta accent passa WCAG-AA texto normal (≥4.5:1) contra `#0e0f15`."""
    contrastes = pagina._validar_contraste_paleta()
    assert contrastes, "Paleta vazia"
    falhas = {cor: r for cor, r in contrastes.items() if r < 4.5}
    assert not falhas, (
        f"Cores abaixo de WCAG-AA contra {CORES['fundo']}: "
        + ", ".join(f"{c}={r:.2f}:1" for c, r in falhas.items())
    )


def test_treemap_paleta_inclui_tokens_canonicos() -> None:
    """Paleta usa tokens de `CORES`, sem hex hardcoded fora da fonte."""
    paleta = set(pagina.PALETA_WCAG_AA)
    esperados = {
        CORES["destaque"],
        CORES["superfluo"],
        CORES["neutro"],
        CORES["positivo"],
        CORES["alerta"],
        CORES["info"],
    }
    faltando = esperados - paleta
    assert not faltando, f"Paleta perdeu tokens canônicos: {faltando}"


# ---------------------------------------------------------------------------
# 2. Árvore expande/colapsa
# ---------------------------------------------------------------------------
def test_arvore_agrupa_por_classificacao_e_categoria(df_categorias: pd.DataFrame) -> None:
    arvore = pagina.calcular_arvore_categorias(df_categorias)
    nomes_familia = [n["classificacao"] for n in arvore]
    assert "Obrigatório" in nomes_familia
    assert "Questionável" in nomes_familia
    questionavel = next(n for n in arvore if n["classificacao"] == "Questionável")
    sub_nomes = {s["categoria"] for s in questionavel["subcategorias"]}
    assert sub_nomes == {"Delivery", "Transporte", "Outros"}
    # ordenado por valor desc
    valores = [s["valor"] for s in questionavel["subcategorias"]]
    assert valores == sorted(valores, reverse=True)


def test_arvore_html_usa_details_expansivel(df_categorias: pd.DataFrame) -> None:
    arvore = pagina.calcular_arvore_categorias(df_categorias)
    total = sum(n["valor"] for n in arvore)
    html = pagina._arvore_html(arvore, total)
    # toggle nativo HTML5
    assert "<details" in html
    assert "<summary>" in html
    # primeira família vem aberta (espelha mockup)
    assert 'open>' in html or 'open ' in html
    # classes canônicas do mockup
    assert "ux-rd-12-cat-row" in html
    assert "ux-rd-12-tree" in html


# ---------------------------------------------------------------------------
# 3. Painel direito mostra regras YAML para categoria selecionada
# ---------------------------------------------------------------------------
def test_carregar_regras_yaml_le_arquivo_real() -> None:
    pagina.carregar_regras_yaml.cache_clear()
    regras = pagina.carregar_regras_yaml()
    assert len(regras) > 0
    # estrutura normalizada
    primeira = regras[0]
    assert {"nome", "regex", "categoria"} <= set(primeira.keys())


def test_agregar_regras_aplicadas_filtra_por_categoria(df_categorias: pd.DataFrame) -> None:
    regras = pagina.carregar_regras_yaml()
    # filtra Delivery -- mockup mostra ifood
    aplicadas = pagina.agregar_regras_aplicadas(df_categorias, regras, "Delivery")
    assert all(r["categoria"] == "Delivery" for r in aplicadas)
    # IFOOD/IFD bate com a regra `delivery`
    hits_total = sum(r["hits"] for r in aplicadas)
    assert hits_total >= 2, f"esperado ≥2 hits para Delivery, vi {hits_total}"


def test_regras_yaml_html_mostra_categoria_no_titulo(df_categorias: pd.DataFrame) -> None:
    regras = pagina.carregar_regras_yaml()
    aplicadas = pagina.agregar_regras_aplicadas(df_categorias, regras, "Delivery")
    html = pagina._regras_yaml_html(aplicadas, "Delivery")
    assert "Delivery" in html
    assert "Regras YAML" in html
    if aplicadas:
        assert "regex" in html  # classe CSS
        assert "hits" in html


# ---------------------------------------------------------------------------
# 4. Click categoria filtra Extrato (drill-down via query_params)
# ---------------------------------------------------------------------------
def test_treemap_usa_aplicar_drilldown_para_extrato(monkeypatch) -> None:
    """O treemap delega click para `aplicar_drilldown` apontando para "Extrato"."""
    chamadas: dict = {}

    def fake_aplicar(fig, *, campo_customdata, tab_destino, key_grafico):
        chamadas["campo"] = campo_customdata
        chamadas["tab"] = tab_destino
        chamadas["key"] = key_grafico

    monkeypatch.setattr(pagina, "aplicar_drilldown", fake_aplicar)
    df = pd.DataFrame(
        [
            {"valor": -100, "categoria": "Aluguel", "classificacao": "Obrigatório"},
            {"valor": -50, "categoria": "Mercado", "classificacao": "Obrigatório"},
        ]
    )
    pagina._treemap_categorias(df)
    assert chamadas["campo"] == "categoria"
    assert chamadas["tab"] == "Extrato"
    assert chamadas["key"] == "treemap_categorias_ux_rd_12"


# ---------------------------------------------------------------------------
# 5. Renderiza em viewport 1200x700 sem corte (UX-115 invariante)
# ---------------------------------------------------------------------------
def test_html_minificado_sem_indentacao_perigosa(df_categorias: pd.DataFrame) -> None:
    """HTML não pode ter linhas com indentação ≥4 espaços (vira `<pre>` do CommonMark)."""
    arvore = pagina.calcular_arvore_categorias(df_categorias)
    total = sum(n["valor"] for n in arvore)
    arv = pagina._arvore_html(arvore, total)
    kpis = pagina.calcular_kpis_categoria(df_categorias)
    kpi_html = pagina._kpis_html(kpis)
    regras_html = pagina._regras_yaml_html([], None)
    for html in (arv, kpi_html, regras_html, pagina._CSS_PAGINA):
        # após minificar não há quebra de linha em sequência indentada
        for linha in html.splitlines():
            assert not linha.startswith("    "), f"linha indentada vaza <pre>: {linha[:80]}"


def test_kpis_calcula_cobertura_e_maior_familia(df_categorias: pd.DataFrame) -> None:
    kpis = pagina.calcular_kpis_categoria(df_categorias)
    assert kpis["transacoes"] == 5
    # 1 das 5 é "Outros" -> cobertura = 80%
    assert kpis["cobertura_pct"] == 80.0
    # Aluguel é a maior categoria por valor (1280 > soma do resto)
    cat_top, valor_top, _ = kpis["maior_familia"]
    assert cat_top == "Aluguel"
    assert valor_top == pytest.approx(1280.0)
    assert kpis["nao_classificadas"] == 1


# ---------------------------------------------------------------------------
# 6. Deep-link `?cluster=Análise&tab=Categorias` HTTP 200
# ---------------------------------------------------------------------------
def test_categorias_no_mapa_aba_para_cluster_analise() -> None:
    """A aba "Categorias" pertence ao cluster "Análise" (deep-link válido)."""
    from src.dashboard.componentes.drilldown import (
        CLUSTERS_VALIDOS,
        MAPA_ABA_PARA_CLUSTER,
    )

    assert "Análise" in CLUSTERS_VALIDOS
    assert MAPA_ABA_PARA_CLUSTER.get("Categorias") == "Análise"


# "Cuide dos centavos e os reais cuidarão de si mesmos." -- Benjamin Franklin
