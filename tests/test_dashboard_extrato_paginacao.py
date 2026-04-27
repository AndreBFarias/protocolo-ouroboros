"""Sprint 92a.8: testes de paginação da tabela do Extrato.

A função pura ``_calcular_slice_pagina`` não depende de ``streamlit``,
por isso é testável sem mock.
"""

from __future__ import annotations

import pytest

from src.dashboard.paginas.extrato import (
    TAMANHO_PAGINA_EXTRATO,
    _calcular_slice_pagina,
)


def test_tamanho_pagina_canonico_e_25() -> None:
    """Spec 92a §item 8: paginação canônica é 25 linhas por página."""
    assert TAMANHO_PAGINA_EXTRATO == 25


@pytest.mark.parametrize(
    "total, pagina, esperado",
    [
        (0, 1, (0, 0)),  # conjunto vazio -> slice vazio
        (10, 1, (0, 10)),  # total < tamanho_pagina, cabe tudo
        (25, 1, (0, 25)),  # exatamente 1 página cheia
        (26, 1, (0, 25)),  # primeira de 2 páginas
        (26, 2, (25, 26)),  # segunda tem 1 linha
        (100, 1, (0, 25)),  # múltiplas páginas: página 1
        (100, 4, (75, 100)),  # página 4 (última)
        (100, 99, (75, 100)),  # clampa para última quando pagina > n_paginas
        (100, 0, (0, 25)),  # clampa para 1 quando pagina < 1
    ],
)
def test_calcular_slice_pagina_cobre_casos_canonicos(
    total: int, pagina: int, esperado: tuple[int, int]
) -> None:
    """Slice é 0-indexado half-open compatível com iloc."""
    assert _calcular_slice_pagina(total, 25, pagina) == esperado


def test_calcular_slice_pagina_com_tamanho_zero_retorna_vazio() -> None:
    """Sanity: tamanho_pagina <= 0 é degenerado, devolve slice vazio."""
    assert _calcular_slice_pagina(100, 0, 1) == (0, 0)
    assert _calcular_slice_pagina(100, -5, 1) == (0, 0)


# "Uma boa medida é aquela que o usuário consegue ajustar." -- princípio de UX
