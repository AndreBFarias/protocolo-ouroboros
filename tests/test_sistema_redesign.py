"""Testes do redesign UX-RD-05 do cluster Sistema.

Validam:
1. Páginas ``skills_d7`` e ``styleguide`` importam sem erro.
2. ``ABAS_POR_CLUSTER["Sistema"]`` contém ["Skills D7", "Styleguide"].
3. ``MAPA_ABA_PARA_CLUSTER`` mapeia ``"Styleguide" -> "Sistema"``.
4. ``styleguide`` renderiza pelo menos um swatch para CADA chave de
   ``CORES`` (regressivo: nova chave em UX-RD-01 deve aparecer aqui).
5. ``skills_d7`` com ``data/output/skill_d7_log.json`` ausente exibe
   fallback graceful (.skill-instr) sem crash.
6. ``skills_d7`` com snapshot mínimo válido renderiza KPIs e lista.
7. AppTest renderiza cluster Sistema sem exception (ambas as abas).
"""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


# ============================================================================
# 1) Páginas importam sem erro
# ============================================================================


class TestImportacao:
    def test_skills_d7_importa(self) -> None:
        from src.dashboard.paginas import skills_d7

        assert hasattr(skills_d7, "renderizar")
        assert callable(skills_d7.renderizar)

    def test_styleguide_importa(self) -> None:
        from src.dashboard.paginas import styleguide

        assert hasattr(styleguide, "renderizar")
        assert callable(styleguide.renderizar)


# ============================================================================
# 2) Cluster Sistema tem 2 abas
# ============================================================================


class TestAbasSistema:
    def test_abas_sistema_inclui_skills_d7_e_styleguide(self) -> None:
        """Sprint UX-DASH-GRADUACAO-TIPOS (2026-05-15) adicionou "Graduação"
        ao cluster Sistema. Mantemos o nome legado do teste por estabilidade
        histórica."""
        from src.dashboard.app import ABAS_POR_CLUSTER

        assert ABAS_POR_CLUSTER["Sistema"] == ["Skills D7", "Styleguide", "Graduação"]

    def test_mapa_aba_styleguide_aponta_para_sistema(self) -> None:
        from src.dashboard.componentes.drilldown import MAPA_ABA_PARA_CLUSTER

        assert MAPA_ABA_PARA_CLUSTER["Styleguide"] == "Sistema"

    def test_invariante_n_para_n_sistema(self) -> None:
        """Toda aba listada em ``ABAS_POR_CLUSTER["Sistema"]`` deve estar
        em ``MAPA_ABA_PARA_CLUSTER`` apontando para "Sistema"."""
        from src.dashboard.app import ABAS_POR_CLUSTER
        from src.dashboard.componentes.drilldown import MAPA_ABA_PARA_CLUSTER

        for aba in ABAS_POR_CLUSTER["Sistema"]:
            assert aba in MAPA_ABA_PARA_CLUSTER, f"{aba} ausente do mapa"
            assert MAPA_ABA_PARA_CLUSTER[aba] == "Sistema"


# ============================================================================
# 3) Styleguide regressivo: todas as chaves de CORES viram swatch
# ============================================================================


class TestStyleguideCobreTodasAsCores:
    def test_swatch_para_cada_chave_de_cores(self) -> None:
        """Regressivo: qualquer chave nova adicionada a CORES (ex: ``d7_*``,
        ``humano_*``) deve aparecer automaticamente como swatch."""
        from src.dashboard.paginas import styleguide
        from src.dashboard.tema import CORES

        html = styleguide._secao_cores_html()
        for chave in CORES:
            # _swatch_para emite ``data-token="<chave>"`` e ``<strong>chave</strong>``.
            assert f'data-token="{chave}"' in html, (
                f"Chave '{chave}' de CORES não aparece como swatch no styleguide"
            )

    def test_swatch_inclui_d7_e_humano(self) -> None:
        """Acceptance UX-RD-05: tokens novos da UX-RD-01 estão presentes."""
        from src.dashboard.paginas import styleguide

        html = styleguide._secao_cores_html()
        for chave in (
            "d7_graduado",
            "d7_calibracao",
            "d7_regredindo",
            "d7_pendente",
            "humano_aprovado",
            "humano_rejeitado",
            "humano_revisar",
            "humano_pendente",
        ):
            assert f'data-token="{chave}"' in html, (
                f"Token '{chave}' deve aparecer no styleguide"
            )


# ============================================================================
# 4) Skills D7 fallback graceful sem snapshot
# ============================================================================


class TestSkillsD7Fallback:
    def test_carregar_snapshot_retorna_none_quando_arquivo_inexistente(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from src.dashboard.paginas import skills_d7

        caminho_inexistente = tmp_path / "skill_d7_log.json"
        monkeypatch.setattr(skills_d7, "CAMINHO_LOG_D7", caminho_inexistente)
        assert skills_d7._carregar_snapshot() is None

    def test_fallback_graceful_html_inclui_skill_instr(self) -> None:
        from src.dashboard.paginas import skills_d7

        html = skills_d7._fallback_graceful_html()
        assert 'class="skill-instr"' in html
        assert "Cobertura D7 ainda não inicializada" in html
        assert "auditar-cobertura-total" in html

    def test_carregar_snapshot_tolerante_a_json_malformado(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from src.dashboard.paginas import skills_d7

        arquivo = tmp_path / "skill_d7_log.json"
        arquivo.write_text("{ json malformado", encoding="utf-8")
        monkeypatch.setattr(skills_d7, "CAMINHO_LOG_D7", arquivo)
        assert skills_d7._carregar_snapshot() is None


# ============================================================================
# 5) Skills D7 com snapshot mínimo
# ============================================================================


class TestSkillsD7ComSnapshot:
    def test_contar_estados_classifica_corretamente(self) -> None:
        from src.dashboard.paginas import skills_d7

        skills = [
            {"id": "s1", "estado": "graduado"},
            {"id": "s2", "estado": "graduado"},
            {"id": "s3", "estado": "calibrando"},
            {"id": "s4", "estado": "regredindo"},
            {"id": "s5", "estado": "pendente"},
            {"id": "s6", "estado": "estado-desconhecido"},  # vira pendente
        ]
        contagens = skills_d7._contar_estados(skills)
        assert contagens["graduado"] == 2
        assert contagens["calibrando"] == 1
        assert contagens["regredindo"] == 1
        assert contagens["pendente"] == 2

    def test_kpi_grid_html_emite_quatro_cards(self) -> None:
        from src.dashboard.paginas import skills_d7

        contagens = {"graduado": 14, "calibrando": 3, "regredindo": 1, "pendente": 0}
        html = skills_d7._kpi_grid_html(contagens, total=18)
        # 4 cards .kpi (cabeçalho graduado, calibrando, regredindo, pendente)
        assert html.count('class="kpi"') == 4
        assert "78%" in html or "78" in html  # cobertura 14/18
        assert "Graduadas" in html
        assert "Calibrando" in html
        assert "Regredindo" in html
        assert "Pendentes" in html

    def test_lista_skills_inclui_pill_para_cada_estado(self) -> None:
        from src.dashboard.paginas import skills_d7

        skills = [
            {
                "nome": "ofx-parse",
                "descricao": "Parser OFX",
                "estado": "graduado",
                "confianca": 0.97,
                "runs": 184,
                "stab": 0.94,
            },
            {
                "nome": "nf-parse",
                "descricao": "Parser NF",
                "estado": "calibrando",
                "confianca": 0.74,
                "runs": 38,
                "stab": 0.68,
            },
        ]
        html = skills_d7._lista_skills_html(skills)
        assert "ofx-parse" in html
        assert "nf-parse" in html
        assert "pill-d7-graduado" in html
        assert "pill-d7-calibracao" in html

    def test_kpis_d7_html_emite_cinco_cards(self) -> None:
        """UX-V-2.8: caminho com snapshot deve renderizar 5 KPIs."""
        from src.dashboard.paginas import skills_d7

        snapshot = {
            "skills": [
                {"estado": "graduado", "confianca": 0.97, "runs": 184},
                {"estado": "graduado", "confianca": 0.94, "runs": 128},
                {"estado": "calibrando", "confianca": 0.74, "runs": 38},
                {"estado": "regredindo", "confianca": 0.62, "runs": 14},
            ],
            "execucoes_30d": 3836,
            "p95_segundos": 2.4,
        }
        contagens = skills_d7._contar_estados(snapshot["skills"])
        html = skills_d7._kpis_d7_html(snapshot, contagens, total=4)
        assert html.count('class="kpi"') == 5
        assert "COBERTURA D7" in html
        assert "TAXA DE GRADUAÇÃO" in html
        assert "REGRESSÕES 30D" in html
        assert "CONFIANÇA MÉDIA" in html
        assert "EXECUÇÕES 30D" in html
        assert "3,836" in html  # execuções formatadas

    def test_distribuicao_estados_html_emite_quatro_celulas(self) -> None:
        """UX-V-2.8: 4 grandes números (graduado/calibrando/regredindo/pendente)."""
        from src.dashboard.paginas import skills_d7

        contagens = {"graduado": 14, "calibrando": 3, "regredindo": 1, "pendente": 0}
        html = skills_d7._distribuicao_estados_html(contagens)
        assert html.count('class="s7-dist-cell"') == 4
        assert "Graduado" in html
        assert "Calibrando" in html
        assert "Regredindo" in html
        assert "Pendente" in html
        assert ">14<" in html
        assert ">3<" in html

    def test_cobertura_cluster_html_lista_clusters(self) -> None:
        """UX-V-2.8: bar chart por cluster quando snapshot fornece."""
        from src.dashboard.paginas import skills_d7

        snapshot = {
            "cobertura_cluster": [
                {"nome": "Finanças", "total": 8, "graduado": 7, "calibrando": 1, "regredindo": 0},
                {"nome": "Documentos", "total": 5, "graduado": 3, "calibrando": 2, "regredindo": 0},
                {"nome": "Análise", "total": 3, "graduado": 2, "calibrando": 0, "regredindo": 1},
                {"nome": "Sistema", "total": 2, "graduado": 2, "calibrando": 0, "regredindo": 0},
            ]
        }
        html = skills_d7._cobertura_cluster_html(snapshot)
        assert html.count('class="s7-cluster-row"') == 4
        assert "Finanças" in html
        assert "Documentos" in html
        assert "Análise" in html
        assert "Sistema" in html
        assert "Cobertura por cluster" in html
        assert "graduado" in html
        assert "calibrando" in html
        assert "regredindo" in html

    def test_cobertura_cluster_html_omite_quando_ausente(self) -> None:
        """Sem ``cobertura_cluster`` e sem campo ``cluster`` nas skills,
        função retorna string vazia (degradação graceful)."""
        from src.dashboard.paginas import skills_d7

        snapshot = {"skills": [{"nome": "x", "estado": "graduado"}]}
        html = skills_d7._cobertura_cluster_html(snapshot)
        assert html == ""

    def test_cobertura_cluster_deriva_de_skills_quando_pre_agregado_ausente(
        self,
    ) -> None:
        """Quando snapshot não traz ``cobertura_cluster`` mas as skills têm
        campo ``cluster``, deriva agregação."""
        from src.dashboard.paginas import skills_d7

        snapshot = {
            "skills": [
                {"nome": "a", "estado": "graduado", "cluster": "Finanças"},
                {"nome": "b", "estado": "graduado", "cluster": "Finanças"},
                {"nome": "c", "estado": "calibrando", "cluster": "Documentos"},
            ]
        }
        html = skills_d7._cobertura_cluster_html(snapshot)
        assert "Finanças" in html
        assert "Documentos" in html
        assert html.count('class="s7-cluster-row"') == 2

    def test_minificar_colapsa_whitespace(self) -> None:
        """Lição UX-RD-04: HTML com indentação >= 4 espaços vira ``<pre>``
        no parser CommonMark do Streamlit. ``_minificar`` previne."""
        from src.dashboard.paginas import skills_d7

        html_indentado = """
            <div>
                <svg><circle cx="10"/></svg>
            </div>
        """
        out = skills_d7._minificar(html_indentado)
        # Não pode ter sequência de 4+ espaços consecutivos
        assert "    " not in out
        assert "<svg>" in out
        assert "<circle" in out


# ============================================================================
# 6) Carregar snapshot real
# ============================================================================


class TestSnapshotReal:
    def test_carregar_snapshot_valido(self, tmp_path: Path, monkeypatch) -> None:
        from src.dashboard.paginas import skills_d7

        snapshot = {
            "gerado_em": "2026-04-29T14:32:00",
            "skills": [
                {
                    "id": "s01",
                    "nome": "ofx-parse",
                    "descricao": "OFX",
                    "estado": "graduado",
                    "confianca": 0.97,
                    "runs": 184,
                    "stab": 0.94,
                }
            ],
            "evolucao": [
                {"semana": 1, "graduadas": 4},
                {"semana": 2, "graduadas": 6},
            ],
        }
        arquivo = tmp_path / "skill_d7_log.json"
        arquivo.write_text(json.dumps(snapshot), encoding="utf-8")
        monkeypatch.setattr(skills_d7, "CAMINHO_LOG_D7", arquivo)

        carregado = skills_d7._carregar_snapshot()
        assert carregado is not None
        assert len(carregado["skills"]) == 1
        assert carregado["skills"][0]["nome"] == "ofx-parse"


# ============================================================================
# 7) Renderização ponta-a-ponta via AppTest
# ============================================================================


class TestRenderizarEndToEnd:
    """Sprint UX-RD-05: integração mínima via Streamlit AppTest. Garante que
    ``renderizar`` não levanta exception em runtime real para AMBAS as
    páginas do cluster Sistema.
    """

    def test_skills_d7_renderiza_sem_crash(self) -> None:
        from streamlit.testing.v1 import AppTest

        script = _script_skills_d7()
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception, [str(e) for e in at.exception]

    def test_skills_d7_sem_snapshot_emite_fallback(self) -> None:
        """Sem skill_d7_log.json, página deve renderizar fallback graceful.

        Atualizado em UX-V-03: a chamada padrão agora aponta para o novo
        _fallback_estado_inicial_html (estado inicial atrativo + CTA mob).
        O _fallback_graceful_html (skill-instr) permanece definido para
        retrocompatibilidade do teste de função pura acima (linha ~123).
        """
        from streamlit.testing.v1 import AppTest

        script = _script_skills_d7_sem_log()
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        # Verifica presença do fallback (novo padrão UX-V-03 OU antigo).
        textos = [m.value for m in at.markdown]
        joined = " ".join(textos)
        assert (
            "fallback-estado" in joined
            or "SKILLS · D7 ainda" in joined
            or "Cobertura D7" in joined
            or "skill-instr" in joined
        )

    def test_styleguide_renderiza_sem_crash(self) -> None:
        from streamlit.testing.v1 import AppTest

        script = _script_styleguide()
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception, [str(e) for e in at.exception]

    def test_styleguide_inclui_secoes_principais(self) -> None:
        from streamlit.testing.v1 import AppTest

        script = _script_styleguide()
        at = AppTest.from_string(script)
        at.run()
        textos = [m.value for m in at.markdown]
        joined = " ".join(textos)
        # Numeração canônica das seções 01..09
        for n in ("01", "02", "03", "04", "05", "06", "07", "08", "09"):
            assert f">{n}<" in joined or f"num\">{n}" in joined, (
                f"Seção {n} ausente do styleguide"
            )


# ----------------------------------------------------------------------------
# Helpers de script (padrão canônico do projeto)
# ----------------------------------------------------------------------------


def _script_skills_d7() -> str:
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
dados = {{"extrato": pd.DataFrame()}}

from src.dashboard.paginas import skills_d7
skills_d7.renderizar(dados, "2026-04", "Todos", None)
"""


def _script_skills_d7_sem_log() -> str:
    """Garante que o caminho do log aponta para arquivo inexistente."""
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
from src.dashboard.paginas import skills_d7

# Força log inexistente no test (pode coexistir com arquivo real em data/output).
skills_d7.CAMINHO_LOG_D7 = Path("/tmp/_definitely_does_not_exist_skill_d7.json")

dados = {{"extrato": pd.DataFrame()}}
skills_d7.renderizar(dados, "2026-04", "Todos", None)
"""


def _script_styleguide() -> str:
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
dados = {{"extrato": pd.DataFrame()}}

from src.dashboard.paginas import styleguide
styleguide.renderizar(dados, "2026-04", "Todos", None)
"""


# "O que se mede, se gerencia." -- Peter Drucker
