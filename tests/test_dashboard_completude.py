"""Testes da aba Completude -- Sprint 92a item 3.

Valida (a) filtro de ruído por volume mínimo de transações, (b) colorscale
trocado para [alerta, info, positivo] (laranja-amarelo-verde, sem vermelho
saturado) -- acceptance criteria da Sprint 92a #3.
"""

from __future__ import annotations

import pandas as pd

from src.dashboard.paginas.completude import (
    LIMIAR_MIN_TX_FILTRO_RUIDO,
    _calcular_kpis_completude,
    _heatmap,
    _kpis_html,
    _legenda_html,
    filtrar_categorias_por_volume,
)

# ---------------------------------------------------------------------------
# Sprint 92a item 3 -- toggle de ruido no heatmap de completude
# ---------------------------------------------------------------------------


def _df_sintetico() -> pd.DataFrame:
    return pd.DataFrame(
        [
            # Aluguel: 3 tx (passa filtro)
            {"categoria": "Aluguel", "valor": 2000.0, "mes_ref": "2026-01"},
            {"categoria": "Aluguel", "valor": 2000.0, "mes_ref": "2026-02"},
            {"categoria": "Aluguel", "valor": 2000.0, "mes_ref": "2026-03"},
            # Energia: 2 tx (passa filtro no limiar exato)
            {"categoria": "Energia", "valor": 120.0, "mes_ref": "2026-01"},
            {"categoria": "Energia", "valor": 130.0, "mes_ref": "2026-02"},
            # Plano de saúde: 1 tx (filtrado pelo ruído)
            {"categoria": "Saúde", "valor": 500.0, "mes_ref": "2026-01"},
            # Água: 0 tx (não aparece em extrato mas está na lista obrigatória)
        ]
    )


def test_filtrar_categorias_por_volume_remove_abaixo_do_limiar() -> None:
    """Categoria com 1 tx é filtrada; >=2 sobrevive."""
    extrato = _df_sintetico()
    obrigatorias = ["Aluguel", "Energia", "Saúde", "Água"]

    resultado = filtrar_categorias_por_volume(extrato, obrigatorias)

    assert "Aluguel" in resultado  # 3 tx
    assert "Energia" in resultado  # 2 tx (limiar exato)
    assert "Saúde" not in resultado  # 1 tx
    assert "Água" not in resultado  # 0 tx


def test_filtrar_categorias_respeita_limiar_parametrizado() -> None:
    """`minimo_tx=3` corta também Energia (2 tx)."""
    extrato = _df_sintetico()
    obrigatorias = ["Aluguel", "Energia"]

    resultado = filtrar_categorias_por_volume(extrato, obrigatorias, minimo_tx=3)

    assert resultado == ["Aluguel"]


def test_filtrar_categorias_extrato_vazio_mantem_lista_intacta() -> None:
    """Sem dados, retorna a lista canônica para não esconder config do usuário."""
    extrato = pd.DataFrame(columns=["categoria", "valor", "mes_ref"])
    obrigatorias = ["Aluguel", "Energia"]

    assert filtrar_categorias_por_volume(extrato, obrigatorias) == obrigatorias


def test_filtrar_categorias_lista_vazia_retorna_lista_vazia() -> None:
    """Sem categorias obrigatórias configuradas, nada a filtrar."""
    extrato = _df_sintetico()
    assert filtrar_categorias_por_volume(extrato, []) == []


def test_limiar_default_e_2_transacoes() -> None:
    """Sprint 92a explicita: limiar default documentado como 2."""  # noqa: accent
    assert LIMIAR_MIN_TX_FILTRO_RUIDO == 2


def test_completude_toggle_reduz_categorias() -> None:
    """Acceptance spec: toggle filtra categorias abaixo do limiar."""
    extrato = _df_sintetico()
    obrigatorias = ["Aluguel", "Energia", "Saúde", "Água"]

    # Toggle ativo (default).
    filtradas = filtrar_categorias_por_volume(extrato, obrigatorias)
    # Toggle desativado: lista completa é usada direto.
    completas = list(obrigatorias)

    assert len(filtradas) < len(completas)
    assert len(filtradas) == 2
    assert len(completas) == 4


# ---------------------------------------------------------------------------
# Sprint 92a item 3 -- colorscale laranja-amarelo-verde (sem vermelho saturado)
# ---------------------------------------------------------------------------


def test_heatmap_usa_colorscale_laranja_amarelo_verde() -> None:
    """Paleta do heatmap NÃO deve ter vermelho saturado (#FF5555) em nenhum stop."""
    from src.dashboard.tema import CORES

    resumo = {
        "2026-01": {"Aluguel": {"total": 2, "com_doc": 1, "sem_doc": 1, "orfas": []}},
        "2026-02": {"Aluguel": {"total": 2, "com_doc": 2, "sem_doc": 0, "orfas": []}},
    }

    fig = _heatmap(resumo)
    assert fig is not None

    heatmap_trace = fig.data[0]
    cores_paleta = [stop[1].lower() for stop in heatmap_trace.colorscale]

    # Paleta nova: alerta (laranja), info (amarelo), positivo (verde).
    assert CORES["alerta"].lower() in cores_paleta
    assert CORES["info"].lower() in cores_paleta
    assert CORES["positivo"].lower() in cores_paleta
    # Paleta antiga usava negativo (vermelho) -- NÃO deve aparecer.
    assert CORES["negativo"].lower() not in cores_paleta


# ---------------------------------------------------------------------------
# Sprint UX-V-2.3 -- 4 KPIs no topo + legenda do heatmap
# ---------------------------------------------------------------------------


def test_calcular_kpis_completude_resumo_vazio_devolve_fallback() -> None:
    """Resumo vazio deve resultar em KPIs zerados (fallback graceful)."""
    kpis = _calcular_kpis_completude({})
    assert kpis == {
        "cobertura": 0.0,
        "tipos_completos": 0,
        "tipos_total": 0,
        "lacunas_criticas": 0,
        "lacunas_medias": 0,
    }


def test_calcular_kpis_completude_calcula_cobertura_global() -> None:
    """Cobertura = com_doc / total agregado, em percentual."""
    resumo = {
        "2026-01": {
            "Aluguel": {"com_doc": 1, "total": 1, "sem_doc": 0, "orfas": []},
            "Energia": {"com_doc": 0, "total": 1, "sem_doc": 1, "orfas": []},
        },
        "2026-02": {
            "Aluguel": {"com_doc": 1, "total": 1, "sem_doc": 0, "orfas": []},
            "Energia": {"com_doc": 0, "total": 1, "sem_doc": 1, "orfas": []},
        },
    }
    kpis = _calcular_kpis_completude(resumo)
    # 2 com_doc / 4 total = 50%.
    assert kpis["cobertura"] == 50.0
    # Aluguel 100% (completo); Energia 0% (crítico).
    assert kpis["tipos_completos"] == 1
    assert kpis["tipos_total"] == 2
    # Energia tem 2 lacunas, < 50% cobertas -> críticas.
    assert kpis["lacunas_criticas"] == 2
    assert kpis["lacunas_medias"] == 0


def test_calcular_kpis_completude_separa_lacunas_criticas_e_medias() -> None:
    """Categorias >=50% cobertas viram médias; <50% viram críticas."""
    resumo = {
        "2026-01": {
            # 75% cobertura -> média (1 lacuna)
            "Aluguel": {"com_doc": 3, "total": 4, "sem_doc": 1, "orfas": []},
            # 25% cobertura -> crítica (3 lacunas)
            "Energia": {"com_doc": 1, "total": 4, "sem_doc": 3, "orfas": []},
        },
    }
    kpis = _calcular_kpis_completude(resumo)
    assert kpis["lacunas_medias"] == 1
    assert kpis["lacunas_criticas"] == 3


def test_kpis_html_renderiza_4_cards_com_classes_canonicas() -> None:
    """HTML deve usar `.kpi-grid` + 4 `.kpi` (UX-M-03 components.css)."""
    html = _kpis_html(
        {
            "cobertura": 84.3,
            "tipos_completos": 2,
            "tipos_total": 5,
            "lacunas_criticas": 3,
            "lacunas_medias": 14,
        }
    )
    assert 'class="kpi-grid"' in html
    assert html.count('class="kpi"') == 4
    assert "84%" in html
    assert "2 / 5" in html
    assert ">3<" in html  # lacunas_criticas
    assert ">14<" in html  # lacunas_medias
    # Labels obrigatórios
    assert "COBERTURA GLOBAL" in html
    assert "TIPOS COMPLETOS" in html
    assert "LACUNAS CRÍTICAS" in html
    assert "LACUNAS MÉDIAS" in html


def test_legenda_html_tem_3_estados_com_cores_d7() -> None:
    """Legenda deve listar completo / parcial / ausente com cores D7."""
    html = _legenda_html()
    assert 'class="completude-legenda"' in html
    assert "completo" in html
    assert "parcial" in html
    assert "ausente" in html
    assert "accent-green" in html
    assert "accent-yellow" in html
    assert "accent-red" in html


# ---------------------------------------------------------------------------
# Sprint UX-V-2.3-FIX -- eixo Y por família documental + chip-bar no header
# ---------------------------------------------------------------------------


def test_familias_documentais_canonicas_casam_mockup_08() -> None:
    """Mockup `08-completude.html` lista exatamente 5 famílias na ordem fixa.

    Garantir que o eixo Y do heatmap real espelha a taxonomia canônica do
    mockup; alterações exigem nova spec UX-V (versionar a expectativa visual).
    """
    from src.dashboard.paginas.completude import FAMILIAS_DOCUMENTAIS

    nomes = [familia for familia, _ids in FAMILIAS_DOCUMENTAIS]
    assert nomes == [
        "OFX bancos",
        "Faturas cartão",
        "Comprovantes Pix",
        "NF serviços",
        "Recibos",
    ]


def test_familia_de_tipo_mapeia_ids_canonicos_yaml() -> None:
    """`tipos_documento.yaml` ids comuns devem cair em sua família correta."""
    from src.dashboard.paginas.completude import _familia_de_tipo

    assert _familia_de_tipo("fatura_cartao") == "Faturas cartão"
    assert _familia_de_tipo("danfe_nfe55") == "NF serviços"
    assert _familia_de_tipo("nfce_modelo_65") == "NF serviços"
    assert _familia_de_tipo("recibo_nao_fiscal") == "Recibos"
    assert _familia_de_tipo("ofx") == "OFX bancos"
    assert _familia_de_tipo("extrato_c6_pdf") == "OFX bancos"


def test_familia_de_tipo_devolve_none_para_tipos_pessoais() -> None:
    """Holerite, IRPF, comprovante CPF -- não pertencem ao contrato visual.

    Esses tipos existem no YAML mas não estão no mockup `08-completude.html`;
    evitamos poluir o heatmap com famílias adicionais.
    """
    from src.dashboard.paginas.completude import _familia_de_tipo

    assert _familia_de_tipo("holerite") is None
    assert _familia_de_tipo("irpf_parcela") is None
    assert _familia_de_tipo("comprovante_cpf") is None
    assert _familia_de_tipo("") is None


def test_calcular_cobertura_documental_marca_full_quando_doc_presente() -> None:
    """Documento `fatura_cartao` em jan/2026 -> família 'Faturas cartão' full."""
    import pandas as pd

    from src.dashboard.paginas.completude import _calcular_cobertura_documental

    df_docs = pd.DataFrame(
        [
            {"tipo_documento": "fatura_cartao", "data_emissao": "2026-01-15"},
        ]
    )
    cobertura = _calcular_cobertura_documental(df_docs, ["2026-01", "2026-02"])
    assert cobertura["2026-01"]["Faturas cartão"]["presente"] == 1
    assert cobertura["2026-01"]["Faturas cartão"]["esperado"] == 1
    # Mês sem documento mantém presente=0.
    assert cobertura["2026-02"]["Faturas cartão"]["presente"] == 0


def test_calcular_cobertura_documental_ignora_tipos_fora_da_taxonomia() -> None:
    """Holerite não polui o heatmap (taxonomia canônica restrita ao mockup)."""
    import pandas as pd

    from src.dashboard.paginas.completude import _calcular_cobertura_documental

    df_docs = pd.DataFrame(
        [
            {"tipo_documento": "holerite", "data_emissao": "2026-01-15"},
            {"tipo_documento": "irpf_parcela", "data_emissao": "2026-02-01"},
        ]
    )
    cobertura = _calcular_cobertura_documental(df_docs, ["2026-01", "2026-02"])
    # Nenhuma família deve ter presente > 0 -- documentos pessoais não contam.
    for cells in cobertura.values():
        for info in cells.values():
            assert info["presente"] == 0


def test_calcular_cobertura_documental_df_vazio_retorna_estrutura_default() -> None:
    """Sem documentos no grafo, todas as células ficam em zero (missing)."""
    import pandas as pd

    from src.dashboard.paginas.completude import (
        FAMILIAS_DOCUMENTAIS,
        _calcular_cobertura_documental,
    )

    df_docs = pd.DataFrame(columns=["tipo_documento", "data_emissao"])
    cobertura = _calcular_cobertura_documental(df_docs, ["2026-01"])
    # Cada família aparece com presente=0 / esperado=1 (full miss).
    for familia, _ids in FAMILIAS_DOCUMENTAIS:
        info = cobertura["2026-01"][familia]
        assert info == {"presente": 0, "esperado": 1}


def test_classificar_celula_documental_tabela_d7() -> None:
    """Tabela canônica presente/esperado -> estado D7."""
    from src.dashboard.paginas.completude import _classificar_celula_documental

    assert _classificar_celula_documental(0, 0) == "empty"
    assert _classificar_celula_documental(1, 1) == "full"
    assert _classificar_celula_documental(2, 1) == "full"
    assert _classificar_celula_documental(0, 1) == "missing"
    assert _classificar_celula_documental(1, 3) == "partial"


def test_matriz_documental_html_renderiza_familias_e_estados() -> None:
    """Matriz documental tem rótulo da família e classes D7 nas células."""
    from src.dashboard.paginas.completude import _matriz_documental_html

    cobertura = {
        "2026-01": {
            "OFX bancos": {"presente": 1, "esperado": 1},
            "Faturas cartão": {"presente": 0, "esperado": 1},
            "Comprovantes Pix": {"presente": 1, "esperado": 3},
            "NF serviços": {"presente": 0, "esperado": 1},
            "Recibos": {"presente": 1, "esperado": 1},
        },
    }
    familias = [
        "OFX bancos",
        "Faturas cartão",
        "Comprovantes Pix",
        "NF serviços",
        "Recibos",
    ]
    html = _matriz_documental_html(cobertura, familias, ["2026-01"])
    # Rótulos das famílias presentes.
    for nome in familias:
        assert nome in html
    # Estados D7 representados como classes CSS.
    assert "completude-cell-full" in html
    assert "completude-cell-missing" in html
    assert "completude-cell-partial" in html
    # Símbolos canônicos do mockup.
    assert ">~<" in html or "~</div>" in html
    assert ">!<" in html or "!</div>" in html


def test_legenda_chip_bar_html_emite_3_chips_canonicos() -> None:
    """Chip-bar à direita do título lista completo/parcial/ausente."""
    from src.dashboard.paginas.completude import _legenda_chip_bar_html

    html = _legenda_chip_bar_html()
    assert 'class="completude-chipbar"' in html
    assert "completo" in html
    assert "parcial" in html
    assert "ausente" in html
    assert "chip-completo" in html
    assert "chip-parcial" in html
    assert "chip-ausente" in html


def test_cobertura_global_documental_calcula_pct_e_lacunas() -> None:
    """Soma presente/esperado e devolve pct global + total de lacunas."""
    from src.dashboard.paginas.completude import _cobertura_global_documental

    cobertura = {
        "2026-01": {
            "OFX bancos": {"presente": 1, "esperado": 1},
            "Faturas cartão": {"presente": 0, "esperado": 1},
        },
        "2026-02": {
            "OFX bancos": {"presente": 1, "esperado": 1},
            "Faturas cartão": {"presente": 1, "esperado": 1},
        },
    }
    pct, lacunas = _cobertura_global_documental(cobertura)
    # 3 presentes / 4 esperados = 75%.
    assert pct == 75.0
    # 1 lacuna remanescente (jan / Faturas cartão).
    assert lacunas == 1


def test_cobertura_global_documental_zero_esperado_devolve_zero() -> None:
    """Cobertura sem expectativa configurada não estoura ZeroDivision."""
    from src.dashboard.paginas.completude import _cobertura_global_documental

    pct, lacunas = _cobertura_global_documental({})
    assert pct == 0.0
    assert lacunas == 0


# "Um heatmap honesto mostra o que falta -- não grita." -- princípio UX
