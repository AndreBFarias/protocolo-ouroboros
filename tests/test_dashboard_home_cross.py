"""Testes do cluster Home cross-tabs -- Sprint UX-123.

Cobre as 4 mini-views novas (`home_dinheiro`, `home_docs`, `home_analise`,
`home_metas`), o helper compartilhado `_home_helpers` e a sincronia entre
`ABAS_POR_CLUSTER` e `MAPA_ABA_PARA_CLUSTER` após a expansão do cluster
Home de 1 para 5 abas.

Padrão canônico do projeto (BRIEF §161): renderizações streamlit testam
via `streamlit.testing.v1.AppTest.from_string(...)`. Helpers puros (sem
chamadas a `st.*`) testam direto com pandas DataFrames.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.dashboard import app as app_mod
from src.dashboard.componentes import drilldown
from src.dashboard.paginas._home_helpers import (
    data_referencia_hoje,
    filtrar_para_hoje,
    renderizar_kpi_compacto,
)

RAIZ = Path(__file__).resolve().parents[1]


# ============================================================================
# 1) Contrato: ordem das abas em ABAS_POR_CLUSTER["Home"]
# ============================================================================


class TestOrdemDasAbasHome:
    def test_home_tem_5_abas_em_ordem_canonica(self) -> None:
        """AC #1: Home tem exatamente 5 abas em ordem fixa.

        Visão Geral em índice 0 preserva URL antiga `?cluster=Home` que
        cai no default. Sprint UX-125: tabs renomeadas para espelhar
        clusters-irmãos (sem sufixo "hoje" repetitivo).
        """
        assert app_mod.ABAS_POR_CLUSTER["Home"] == [
            "Visão Geral",
            "Finanças",
            "Documentos",
            "Análise",
            "Metas",
        ]

    def test_visao_geral_continua_em_indice_0(self) -> None:
        """Default do cluster Home permanece Visão Geral (compat URL antiga)."""
        assert app_mod.ABAS_POR_CLUSTER["Home"][0] == "Visão Geral"

    def test_mini_views_homonimas_nao_mapeiam_para_home(self) -> None:
        """Sprint UX-125: tabs do Home homônimas com clusters próprios
        (Finanças/Documentos/Análise/Metas) NÃO aparecem como entrada
        para 'Home' em MAPA_ABA_PARA_CLUSTER -- a chave do dict é única
        e pertence ao cluster canônico próprio. Tabs do Home são
        acessadas com ?cluster=Home&tab=Finanças (cluster explícito).
        """
        for aba in drilldown.ABAS_HOME_HOMONIMAS:
            if aba in drilldown.MAPA_ABA_PARA_CLUSTER:
                # "Análise" e "Metas" existem no MAPA pelo cluster próprio.
                # Garantia: nunca apontam para "Home".
                assert drilldown.MAPA_ABA_PARA_CLUSTER[aba] != "Home", (
                    f"Aba homônima '{aba}' não pode mapear para 'Home' "
                    f"(homonímia consciente UX-125)"
                )


# ============================================================================
# 2) Helper filtrar_para_hoje
# ============================================================================


class TestFiltrarParaHoje:
    def test_dataframe_vazio_retorna_vazio(self) -> None:
        df = pd.DataFrame(columns=["data", "valor"])
        resultado = filtrar_para_hoje(df)
        assert resultado.empty

    def test_data_de_hoje_real_passa(self) -> None:
        """Se o dataset tem `date.today()`, esse dia é a referência."""
        hoje = date.today().strftime("%Y-%m-%d")
        df = pd.DataFrame(
            {"data": [hoje, "2025-01-01", hoje, "2024-06-15"], "valor": [10, 20, 30, 40]}
        )
        resultado = filtrar_para_hoje(df)
        assert len(resultado) == 2
        assert set(resultado["valor"]) == {10, 30}

    def test_sem_data_de_hoje_usa_mais_recente(self) -> None:
        """Sem `date.today()` no dataset, usa o último dia disponível."""
        df = pd.DataFrame(
            {
                "data": ["2024-06-15", "2024-06-15", "2024-06-10"],
                "valor": [10, 20, 30],
            }
        )
        resultado = filtrar_para_hoje(df)
        assert len(resultado) == 2
        assert set(resultado["valor"]) == {10, 20}

    def test_coluna_data_alternativa(self) -> None:
        """`coluna_data` configurável (ex: 'data_emissao' para docs)."""
        df = pd.DataFrame(
            {
                "data_emissao": ["2026-04-20", "2026-04-19"],
                "id": [1, 2],
            }
        )
        resultado = filtrar_para_hoje(df, coluna_data="data_emissao")
        assert len(resultado) == 1
        assert resultado.iloc[0]["id"] == 1

    def test_sem_coluna_de_data_devolve_df_intacto(self) -> None:
        """Defensivo: se a coluna não existe, devolve df original."""
        df = pd.DataFrame({"valor": [1, 2, 3]})
        resultado = filtrar_para_hoje(df, coluna_data="data")
        assert len(resultado) == 3

    def test_data_referencia_hoje_devolve_string_iso(self) -> None:
        """`data_referencia_hoje` devolve YYYY-MM-DD."""
        df = pd.DataFrame({"data": ["2026-04-20", "2026-04-15"]})
        ref = data_referencia_hoje(df)
        assert ref == "2026-04-20"

    def test_data_referencia_hoje_em_df_vazio_devolve_none(self) -> None:
        ref = data_referencia_hoje(pd.DataFrame())
        assert ref is None


# ============================================================================
# 3) Helper renderizar_kpi_compacto (puro: gera HTML)
# ============================================================================


class TestRenderizarKpiCompacto:
    def test_inclui_titulo_e_valor_no_html(self) -> None:
        html = renderizar_kpi_compacto("Receita", "R$ 100,00", "#50fa7b")
        assert "Receita" in html
        assert "R$ 100,00" in html

    def test_aceita_valor_nao_string_via_str_coerce(self) -> None:
        """Aceita int/float -- helper aplica `str(valor)`."""
        html = renderizar_kpi_compacto("Total", 42, "#bd93f9")
        assert "42" in html


# ============================================================================
# 4) Renderização das 4 mini-views via AppTest (smoke -- não crasha)
# ============================================================================


class TestMiniViewsRenderizamSemCrash:
    """Cada mini-view roda em AppTest com dataset mínimo. Se ocorre
    qualquer exception não tratada em `renderizar()`, AppTest captura.
    """

    def test_home_dinheiro_renderiza_com_extrato_minimo(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from streamlit.testing.v1 import AppTest

        script = _script_home_dinheiro()
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception

    def test_home_docs_renderiza_com_grafo_ausente(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Graceful degradation (ADR-10): grafo ausente mostra warning,
        não crasha."""
        from streamlit.testing.v1 import AppTest

        inexistente = tmp_path / "nao_existe.sqlite"
        script = _script_home_docs(inexistente)
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        textos = (
            [w.value for w in at.warning]
            + [i.value for i in at.info]
            + [m.value for m in at.markdown]
        )
        assert any("grafo" in t.lower() or "popule" in t.lower() for t in textos)

    def test_home_analise_renderiza_com_extrato_minimo(self) -> None:
        from streamlit.testing.v1 import AppTest

        script = _script_home_analise()
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception

    def test_home_metas_renderiza_sem_metas_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Metas yaml ausente: warning, não crasha."""
        from streamlit.testing.v1 import AppTest

        script = _script_home_metas(tmp_path / "metas_ausente.yaml")
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception


# ============================================================================
# 5) Integração: app.py declara as 5 abas no st.tabs do cluster Home
# ============================================================================


class TestIntegracaoAppPy:
    def test_app_py_declara_5_tabs_no_cluster_home(self) -> None:
        """Inspeção textual: app.py contém st.tabs com as 5 abas do Home.

        Sprint UX-125: tabs renomeadas para 'Finanças', 'Documentos',
        'Análise', 'Metas' (sem sufixo 'hoje').
        """
        texto = (RAIZ / "src" / "dashboard" / "app.py").read_text(encoding="utf-8")
        # Os nomes aparecem em duas posições: na lista ABAS_POR_CLUSTER["Home"]
        # e na chamada st.tabs([...]). Confirma que estão presentes.
        for aba in ("Visão Geral", "Finanças", "Documentos", "Análise", "Metas"):
            assert f'"{aba}"' in texto, f"Aba '{aba}' deveria aparecer em app.py"
        # Sprint UX-125: 'Dinheiro hoje' não deve mais existir como string.
        assert '"Dinheiro hoje"' not in texto
        assert '"Docs hoje"' not in texto

    def test_app_py_chama_renderizar_das_4_mini_views(self) -> None:
        """Sprint UX-125: arquivos físicos (home_dinheiro.py etc.) mantêm
        nome interno; só os labels mudaram. Nomes dos módulos persistem."""
        texto = (RAIZ / "src" / "dashboard" / "app.py").read_text(encoding="utf-8")
        assert "home_dinheiro.renderizar" in texto
        assert "home_docs.renderizar" in texto
        assert "home_analise.renderizar" in texto
        assert "home_metas.renderizar" in texto


# ============================================================================
# Scripts de AppTest (helpers de geração)
# ============================================================================


def _script_home_dinheiro() -> str:
    """Gera script Streamlit que renderiza home_dinheiro com extrato fake."""
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd

extrato = pd.DataFrame({{
    "data": ["2026-04-20", "2026-04-20", "2026-04-15"],
    "mes_ref": ["2026-04", "2026-04", "2026-04"],
    "valor": [50.0, 30.0, 100.0],
    "tipo": ["Despesa", "Receita", "Despesa"],
    "categoria": ["Mercado", "Salário", "Combustível"],
    "classificacao": ["Obrigatório", "N/A", "Obrigatório"],
    "local": ["Padaria X", "Empresa Y", "Posto Z"],
    "banco_origem": ["Itaú", "Itaú", "Nubank"],
    "quem": ["André", "André", "André"],
    "forma_pagamento": ["Pix", "Transferência", "Crédito"],
}})
dados = {{"extrato": extrato}}

from src.dashboard.paginas import home_dinheiro
home_dinheiro.renderizar(dados, "2026-04", "Todos", None)
"""


def _script_home_docs(caminho_grafo: Path) -> str:
    """Gera script Streamlit que renderiza home_docs apontando para grafo
    customizado (possivelmente inexistente)."""
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.dashboard import dados as d
d.CAMINHO_GRAFO = Path({str(caminho_grafo)!r})
d.carregar_documentos_grafo.clear()

from src.dashboard.paginas import home_docs
home_docs.renderizar()
"""


def _script_home_analise() -> str:
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd

extrato = pd.DataFrame({{
    "data": ["2026-04-20", "2026-04-20", "2026-04-20"],
    "mes_ref": ["2026-04", "2026-04", "2026-04"],
    "valor": [50.0, 30.0, 80.0],
    "tipo": ["Despesa", "Despesa", "Despesa"],
    "categoria": ["Mercado", "Mercado", "Combustível"],
    "classificacao": ["Obrigatório", "Obrigatório", "Obrigatório"],
    "local": ["Padaria X", "Padaria X", "Posto Z"],
    "banco_origem": ["Itaú", "Itaú", "Nubank"],
    "quem": ["André", "André", "André"],
    "forma_pagamento": ["Pix", "Pix", "Crédito"],
}})
dados = {{"extrato": extrato}}

from src.dashboard.paginas import home_analise
home_analise.renderizar(dados, "2026-04", "Todos", None)
"""


def _script_home_metas(caminho_metas: Path) -> str:
    """Renderiza home_metas sem metas.yaml: deve mostrar warning."""
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
from src.dashboard.paginas import metas as metas_mod
metas_mod.CAMINHO_METAS = Path({str(caminho_metas)!r})

dados = {{"extrato": pd.DataFrame()}}

from src.dashboard.paginas import home_metas
home_metas.renderizar(dados, "2026-04", "Todos", None)
"""


# "Cinco janelas pequenas valem mais que uma porta gigante." -- princípio de UX
