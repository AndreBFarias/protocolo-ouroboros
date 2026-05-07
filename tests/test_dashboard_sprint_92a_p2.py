"""Testes de regressão dos 3 fixes P2 da Sprint 92a.

- Item 11: `ROTULOS_TIPO_DOCUMENTO` inclui `irpf_parcela`, `das_mei`,
  `comprovante_cpf` — 3 tipos introduzidos na Sprint 87.4
  (`mappings/tipos_documento.yaml`) mas até agora sem label humano
  na aba Catalogação, aparecendo como chave técnica crua.
- Item 12: `_renderizar_sankey` injeta `hovertemplate` no `link=`
  do Plotly com padrão `source → target<br>R$ valor`.
- Item 13: `_renderizar_extrato` inclui `st.caption` com legenda da
  coluna "Doc?" abaixo da tabela.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


def test_rotulos_tipo_documento_inclui_novos_tipos_sprint_87_4() -> None:
    """Item 11: labels humanos para `irpf_parcela`, `das_mei`, `comprovante_cpf`."""
    from src.dashboard.paginas.catalogacao import ROTULOS_TIPO_DOCUMENTO

    for chave, esperado in (
        ("irpf_parcela", "Parcela IRPF"),
        ("das_mei", "DAS MEI"),
        ("comprovante_cpf", "Comprovante CPF"),
    ):
        assert chave in ROTULOS_TIPO_DOCUMENTO, (
            f"Label humano ausente para {chave}; aba Catalogação exibirá "
            f"chave técnica crua em vez de {esperado!r}."
        )
        assert ROTULOS_TIPO_DOCUMENTO[chave] == esperado


def test_sankey_injeta_hovertemplate_com_valor_formatado_em_reais() -> None:
    """Item 12: `link=` do Sankey carrega hovertemplate PT-BR com moeda.

    Sprint UX-RD-13: `_renderizar_sankey` foi consolidado em
    `_renderizar_aba_fluxo` (KPIs + Sankey). Sprint UX-V-2.6 extraiu o
    Sankey para `_renderizar_sankey_inline` para suportar layout em
    colunas. A invariante semântica permanece: hovertemplate PT-BR com R$.
    """
    from src.dashboard.paginas import analise_avancada

    # Inspeciona o helper canônico do Sankey (extraído por UX-V-2.6) com
    # fallback para o entrypoint da aba (compat com versões anteriores).
    fonte_sankey = getattr(
        analise_avancada,
        "_renderizar_sankey_inline",
        analise_avancada._renderizar_aba_fluxo,
    )
    source = inspect.getsource(fonte_sankey)

    assert "hovertemplate" in source, (
        "Sankey precisa de hovertemplate (item 12 Sprint 92a P2): sem ele, "
        "links mostram apenas valor cru sem contexto de moeda."
    )
    assert "R$" in source and "%{value:,.2f}" in source, (
        "hovertemplate do Sankey deve exibir valor em reais formatado (R$ %{value:,.2f})."
    )


def test_extrato_exibe_caption_com_legenda_da_coluna_doc() -> None:
    """Item 13: legenda textual da coluna `Doc?` abaixo da tabela do Extrato.

    Sprint 92c: a legenda deixou de ser ``st.caption`` (texto simples) e
    passou a ser ``st.markdown`` com HTML contendo ícones Feather inline
    (check-circle verde, alert-triangle laranja) + os rótulos PT-BR
    ``Doc ok`` / ``Faltando``. A invariante educativa permanece: o usuário
    precisa saber o que cada marcador significa.
    """
    caminho = Path(__file__).parent.parent / "src" / "dashboard" / "paginas" / "extrato.py"
    source = caminho.read_text(encoding="utf-8")

    assert "Doc?" in source, "Referência à coluna 'Doc?' ausente do Extrato."
    assert "documento vinculado no grafo" in source, (
        "Texto explicativo do marcador 'Doc ok' ausente; legenda não educa o usuário."
    )
    assert 'icon_html("check-circle"' in source or 'icon_html("check-circle"' in source, (
        "Legenda da coluna Doc? precisa usar icon_html('check-circle', ...) (Sprint 92c)."
    )
    assert 'icon_html("alert-triangle"' in source or 'icon_html("alert-triangle"' in source, (
        "Legenda da coluna Doc? precisa usar icon_html('alert-triangle', ...) (Sprint 92c)."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# "Minúcias que o dashboard explica são frustrações que o usuário evita."
# -- princípio da legenda honesta
