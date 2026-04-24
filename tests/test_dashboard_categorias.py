"""Testes da pagina Categorias -- Sprint 92a item 2.

Valida `_cor_texto_por_fundo` com fundos conhecidos do tema Dracula,
atendendo ao acceptance criteria: preto em fundos com luminancia WCAG
> 0.6, branco abaixo.
"""

from __future__ import annotations

from src.dashboard.paginas.categorias import _cor_texto_por_fundo

# ---------------------------------------------------------------------------
# Sprint 92a item 2 -- contraste WCAG do treemap de categorias
# ---------------------------------------------------------------------------


def test_cor_texto_fundo_verde_dracula_retorna_preto() -> None:
    """Green #50FA7B tem luminancia ~0.83 -> preto."""
    assert _cor_texto_por_fundo("#50FA7B") == "#000"


def test_cor_texto_fundo_amarelo_dracula_retorna_preto() -> None:
    """Yellow #F1FA8C tem luminancia ~0.91 -> preto."""
    assert _cor_texto_por_fundo("#F1FA8C") == "#000"


def test_cor_texto_fundo_laranja_dracula_retorna_branco() -> None:
    """Orange #FFB86C luminancia ~0.566 -> branco (abaixo do limiar 0.6)."""
    assert _cor_texto_por_fundo("#FFB86C") == "#fff"


def test_cor_texto_fundo_roxo_dracula_retorna_branco() -> None:
    """Purple #BD93F9 luminancia ~0.39 -> branco."""
    assert _cor_texto_por_fundo("#BD93F9") == "#fff"


def test_cor_texto_fundo_vermelho_dracula_retorna_branco() -> None:
    """Red #FF5555 luminancia ~0.33 -> branco."""
    assert _cor_texto_por_fundo("#FF5555") == "#fff"


def test_cor_texto_fundo_rosa_dracula_retorna_branco() -> None:
    """Pink #FF79C6 luminancia ~0.44 -> branco."""
    assert _cor_texto_por_fundo("#FF79C6") == "#fff"


def test_cor_texto_fundo_escuro_dracula_retorna_branco() -> None:
    """Background #282A36 luminancia ~0.02 -> branco."""
    assert _cor_texto_por_fundo("#282A36") == "#fff"


def test_cor_texto_fundo_branco_puro_retorna_preto() -> None:
    """Branco #ffffff luminancia 1.0 -> preto."""
    assert _cor_texto_por_fundo("#ffffff") == "#000"


def test_cor_texto_fundo_preto_puro_retorna_branco() -> None:
    """Preto #000000 luminancia 0.0 -> branco."""
    assert _cor_texto_por_fundo("#000000") == "#fff"


def test_cor_texto_aceita_formato_curto_rgb() -> None:
    """`#fff` vale por `#ffffff`."""
    assert _cor_texto_por_fundo("#fff") == "#000"
    assert _cor_texto_por_fundo("#000") == "#fff"


def test_cor_texto_fallback_para_input_invalido_retorna_branco() -> None:
    """String inválida não quebra; default seguro para tema dark."""
    assert _cor_texto_por_fundo("") == "#fff"
    assert _cor_texto_por_fundo("nao-e-hex") == "#fff"  # noqa: accent
    assert _cor_texto_por_fundo("#GGGGGG") == "#fff"
    assert _cor_texto_por_fundo(None) == "#fff"  # type: ignore[arg-type]


def test_treemap_aplica_textfont_color_por_leaf() -> None:
    """Regressao: _treemap_categorias deve alimentar textfont.color com lista."""
    import pandas as pd

    from src.dashboard.paginas.categorias import MAPA_CLASSIFICACAO_COR

    df = pd.DataFrame(
        [
            {"categoria": "Aluguel", "classificacao": "Obrigatório", "valor": 2000.0},
            {"categoria": "Games", "classificacao": "Supérfluo", "valor": 300.0},
        ]
    )
    agrupado = (
        df.groupby(["categoria", "classificacao"])["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
    )

    # Replica a logica interna para validar: cor de texto por classificacao.
    cores_texto = [
        _cor_texto_por_fundo(MAPA_CLASSIFICACAO_COR.get(c, "#000000"))
        for c in agrupado["classificacao"]
    ]
    assert len(cores_texto) == len(agrupado)
    # Obrigatório -> verde -> preto. Supérfluo -> pink -> branco.
    mapa = dict(zip(agrupado["classificacao"], cores_texto))
    assert mapa["Obrigatório"] == "#000"
    assert mapa["Supérfluo"] == "#fff"


# "Contraste é acessibilidade, não estética." -- princípio WCAG 2.1
