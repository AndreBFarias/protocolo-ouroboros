"""Testes da Sprint UX-RD-17 -- Bem-estar / Hoje + Humor.

Cobre:
  1.  ``escrever_registro`` grava daily/<YYYY-MM-DD>.md no vault.
  2.  Idempotência: mesmo dia/pessoa sobrescreve preservando timestamp_criacao.
  3.  Cache regenera após gravar (próxima leitura mostra novo dia).
  4.  Sliders fora de 1..5 -> ValueError.
  5.  ``gerar_heatmap_html`` 91 dias produz N células (incluindo vazias).
  6.  Overlay diagonal aparece quando pessoa="ambos" e há registros A+B.
  7.  Opacity 50% (0.5) presente nas células overlay.
  8.  Vault inexistente: páginas renderizam sem crash (fallback graceful).
  9.  Contrato deep-link: ?cluster=Bem-estar&tab=Hoje resolve cluster.
 10.  Contrato deep-link: ?cluster=Bem-estar&tab=Humor resolve cluster.
 11.  Invariante N:N -- todas as 12 abas em ABAS_POR_CLUSTER["Bem-estar"]
       estão em MAPA_ABA_PARA_CLUSTER apontando para "Bem-estar".
 12.  ``cor_para_humor`` mapeia 1..5 corretamente; fora do range -> transparent.

Padrão UX-RD herdado: testes não exigem dashboard rodando -- apenas
verificam contratos puros e shape de strings.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.dashboard.componentes.heatmap_humor import (
    cor_para_humor,
    gerar_heatmap_html,
)
from src.mobile_cache.escrever_humor import (
    TAGS_CANONICAS,
    escrever_registro,
)
from src.mobile_cache.humor_heatmap import gerar_humor_heatmap

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _vault_sintetico(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "daily").mkdir(parents=True)
    (vault / "inbox" / "mente" / "humor").mkdir(parents=True)
    return vault


def _ler_frontmatter(arquivo: Path) -> dict[str, Any]:
    texto = arquivo.read_text(encoding="utf-8")
    assert texto.startswith("---\n")
    bloco_yaml = texto.split("---", 2)[1]
    return yaml.safe_load(bloco_yaml) or {}


# ============================================================================
# 1. Gravação básica
# ============================================================================


def test_escrever_registro_grava_md_no_vault(tmp_path: Path) -> None:
    vault = _vault_sintetico(tmp_path)
    dia = date(2026, 5, 5)

    arquivo = escrever_registro(
        vault,
        dia,
        humor=4,
        energia=3,
        ansiedade=2,
        foco=4,
        medicacao=True,
        horas_sono=6.5,
        tags=["calma", "foco"],
        frase="manhã produtiva, sono ok",
        pessoa="pessoa_a",
    )

    assert arquivo.exists()
    assert arquivo.parent == vault / "daily"
    assert arquivo.name == "2026-05-05.md"

    fm = _ler_frontmatter(arquivo)
    assert fm["tipo"] == "humor"
    assert fm["data"] == "2026-05-05"
    assert fm["autor"] == "pessoa_a"
    assert fm["humor"] == 4
    assert fm["energia"] == 3
    assert fm["ansiedade"] == 2
    assert fm["foco"] == 4
    assert fm["medicacao_tomada"] is True
    assert fm["horas_sono"] == 6.5
    assert fm["tags"] == ["calma", "foco"]


# ============================================================================
# 2. Idempotência
# ============================================================================


def test_escrever_registro_sobrescreve_preserva_timestamp_criacao(
    tmp_path: Path,
) -> None:
    vault = _vault_sintetico(tmp_path)
    dia = date(2026, 5, 5)

    arquivo_1 = escrever_registro(
        vault, dia, humor=3, energia=3, ansiedade=3, foco=3, pessoa="pessoa_a"
    )
    fm_1 = _ler_frontmatter(arquivo_1)
    ts_criacao_1 = fm_1["timestamp_criacao"]

    # Re-gravar mesmo dia/pessoa -- timestamp_criacao deve persistir.
    arquivo_2 = escrever_registro(
        vault, dia, humor=5, energia=4, ansiedade=2, foco=5, pessoa="pessoa_a"
    )
    assert arquivo_2 == arquivo_1
    fm_2 = _ler_frontmatter(arquivo_2)
    assert fm_2["timestamp_criacao"] == ts_criacao_1
    assert fm_2["humor"] == 5
    # timestamp_atualizacao pode mudar -- mas timestamp_criacao não.


# ============================================================================
# 3. Cache regenera
# ============================================================================


def test_escrever_registro_regenera_cache_humor_heatmap(tmp_path: Path) -> None:
    vault = _vault_sintetico(tmp_path)
    dia = date(2026, 5, 5)

    cache_path = vault / ".ouroboros" / "cache" / "humor-heatmap.json"
    assert not cache_path.exists()

    escrever_registro(
        vault,
        dia,
        humor=4,
        energia=3,
        ansiedade=2,
        foco=4,
        pessoa="pessoa_a",
    )

    assert cache_path.exists()
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    celulas = payload.get("celulas", [])
    # O cache só inclui dias dentro de periodo_dias (default 90) a partir
    # de date.today(). Aceitamos lista vazia se 2026-05-05 está fora da
    # janela; mas se está dentro, a célula recém-gravada deve aparecer.
    hoje = date.today()
    if hoje - timedelta(days=89) <= dia <= hoje:
        autores = {(c["data"], c["autor"]) for c in celulas}
        assert ("2026-05-05", "pessoa_a") in autores
    # Em ambos os casos o arquivo JSON existe (regeração ocorreu).


# ============================================================================
# 4. Validação de range
# ============================================================================


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("humor", 0),
        ("humor", 6),
        ("energia", -1),
        ("ansiedade", 10),
        ("foco", 7),
    ],
)
def test_escrever_registro_slider_fora_de_1_5_estoura(
    tmp_path: Path, campo: str, valor: int
) -> None:
    vault = _vault_sintetico(tmp_path)
    dia = date(2026, 5, 5)
    kwargs = {"humor": 3, "energia": 3, "ansiedade": 3, "foco": 3}
    kwargs[campo] = valor
    with pytest.raises(ValueError, match=campo):
        escrever_registro(vault, dia, pessoa="pessoa_a", **kwargs)


# ============================================================================
# 5. Heatmap 91 cells
# ============================================================================


def test_gerar_heatmap_html_91_dias_produz_91_cells() -> None:
    items: list[dict[str, Any]] = []
    hoje = date(2026, 5, 5)
    html = gerar_heatmap_html(items, pessoa="pessoa_a", periodo_dias=91, hoje=hoje)
    # 13 colunas × 7 linhas = 91 dias. Cada célula tem ``class="cell ..."``.
    # Conta o marker base ``class="cell `` (com espaço antes do próximo
    # token) -- robusto a múltiplas combinações ``vazio``/``hoje``/etc.
    n_cells = html.count('class="cell ')
    assert n_cells == 91, f"esperava 91 células, obtive {n_cells}"
    # Quando items=[], a maioria deve estar marcada como ``vazio``.
    n_vazios = html.count("vazio")
    assert n_vazios >= 80, f"esperava ≥80 células vazias, obtive {n_vazios}"


def test_gerar_heatmap_html_renderiza_celulas_coloridas_quando_ha_registros() -> None:
    hoje = date(2026, 5, 5)
    items = [
        {"data": hoje.isoformat(), "autor": "pessoa_a", "humor": 5},
        {"data": (hoje - timedelta(days=1)).isoformat(), "autor": "pessoa_a", "humor": 1},
    ]
    html = gerar_heatmap_html(items, pessoa="pessoa_a", periodo_dias=91, hoje=hoje)
    # Cor humor=5 = positivo (#50fa7b verde) e humor=1 = negativo (#ff5555 vermelho)
    assert "#50fa7b" in html
    assert "#ff5555" in html


# ============================================================================
# 6 + 7. Overlay pessoa_a / pessoa_b com 50% opacity
# ============================================================================


def test_gerar_heatmap_html_overlay_ambos_aplica_opacity_50() -> None:
    hoje = date(2026, 5, 5)
    items = [
        {"data": hoje.isoformat(), "autor": "pessoa_a", "humor": 4},
        {"data": hoje.isoformat(), "autor": "pessoa_b", "humor": 2},
    ]
    html = gerar_heatmap_html(items, pessoa="ambos", periodo_dias=91, hoje=hoje)
    # Classe heatmap-overlay presente quando ambos os autores têm registro.
    assert "heatmap-overlay" in html
    # Opacity 0.5 inline nas células overlay (mockup 18: "50% opacity").
    assert "opacity:0.5" in html
    # Linear-gradient diagonal 135deg (overlay diagonal A+B).
    assert "linear-gradient(135deg" in html


# ============================================================================
# 8. Fallback graceful: vault inexistente
# ============================================================================


def test_be_hoje_renderiza_sem_crash_quando_vault_ausente(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``be_hoje.renderizar`` mostra warning sem estourar quando vault=None."""
    from src.dashboard.paginas import be_hoje

    chamadas: list[tuple[str, Any]] = []

    class _FakeSt:
        def __init__(self) -> None:
            self.session_state: dict = {}

        def markdown(self, *a, **kw):
            chamadas.append(("markdown", a))

        def warning(self, msg: str) -> None:
            chamadas.append(("warning", msg))

        def info(self, msg: str) -> None:
            chamadas.append(("info", msg))

        def success(self, msg: str) -> None:
            chamadas.append(("success", msg))

        def error(self, msg: str) -> None:
            chamadas.append(("error", msg))

        def columns(self, spec):
            class _Col:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, *exc):
                    return False

            return [_Col() for _ in (spec if isinstance(spec, list) else range(len(spec)))]

    fake = _FakeSt()
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    monkeypatch.setattr(be_hoje, "st", fake)
    # Vault inexistente: descobrir_vault_root retorna None
    monkeypatch.setattr(be_hoje, "descobrir_vault_root", lambda: None)

    be_hoje.renderizar({}, "mes_atual", "pessoa_a", None)

    tipos = [c[0] for c in chamadas]
    assert "warning" in tipos, f"esperava warning quando vault=None, obtive {tipos}"


# ============================================================================
# 9 + 10. Deep-link ?cluster=Bem-estar&tab=Hoje / Humor
# ============================================================================


class _FakeStCluster:
    def __init__(self, qp: dict[str, Any]) -> None:
        self.session_state: dict = {}
        self.query_params = qp


def test_deep_link_cluster_bem_estar_tab_hoje(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.dashboard.componentes import drilldown

    fake = _FakeStCluster({"cluster": "Bem-estar", "tab": "Hoje"})
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    drilldown.ler_filtros_da_url()
    assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Bem-estar"
    assert fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Hoje"


def test_deep_link_cluster_bem_estar_tab_humor(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.dashboard.componentes import drilldown

    fake = _FakeStCluster({"cluster": "Bem-estar", "tab": "Humor"})
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    drilldown.ler_filtros_da_url()
    assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Bem-estar"
    assert fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Humor"


# ============================================================================
# 11. Invariante N:N
# ============================================================================


def test_invariante_n_para_n_bem_estar() -> None:
    from src.dashboard.app import ABAS_POR_CLUSTER
    from src.dashboard.componentes.drilldown import MAPA_ABA_PARA_CLUSTER

    abas_bem_estar = ABAS_POR_CLUSTER["Bem-estar"]
    assert len(abas_bem_estar) == 12, (
        f"esperava 12 abas em Bem-estar, obtive {len(abas_bem_estar)}"
    )
    for aba in abas_bem_estar:
        assert aba in MAPA_ABA_PARA_CLUSTER, (
            f"aba '{aba}' do cluster Bem-estar ausente do mapa"
        )
        assert MAPA_ABA_PARA_CLUSTER[aba] == "Bem-estar", (
            f"aba '{aba}' aponta para "
            f"'{MAPA_ABA_PARA_CLUSTER[aba]}' em vez de 'Bem-estar'"
        )


# ============================================================================
# 12. cor_para_humor mapping
# ============================================================================


@pytest.mark.parametrize(
    "valor,esperado_substr",
    [
        (1, "ff5555"),  # red
        (2, "ffb86c"),  # orange
        (3, "f1fa8c"),  # yellow
        (4, "8be9fd"),  # cyan
        (5, "50fa7b"),  # green
    ],
)
def test_cor_para_humor_mapeia_paleta(valor: int, esperado_substr: str) -> None:
    cor = cor_para_humor(valor)
    assert esperado_substr in cor.lower(), (
        f"humor={valor}: esperava cor contendo '{esperado_substr}', obtive '{cor}'"
    )


@pytest.mark.parametrize("valor", [0, -1, 6, 100, None, "abc"])
def test_cor_para_humor_fora_do_range_retorna_transparent(valor: Any) -> None:
    assert cor_para_humor(valor) == "transparent"


# ============================================================================
# 13. Tags canônicas
# ============================================================================


def test_tags_canonicas_inclui_chips_do_mockup() -> None:
    """Mockup 17 lista 8 chips: alegria, ansiedade, calma, cansaço, foco,
    irritação, tranquilidade, gratidão."""
    esperadas = {
        "alegria",
        "ansiedade",
        "calma",
        "cansaço",
        "foco",
        "irritação",
        "tranquilidade",
        "gratidão",
    }
    assert set(TAGS_CANONICAS) == esperadas


# ============================================================================
# 14. Cache existente: gerar_humor_heatmap encontra arquivo recém-gravado
# ============================================================================


def test_proxima_leitura_apos_gravacao_mostra_novo_dia(tmp_path: Path) -> None:
    """Gate ANTES → DURANTE → DEPOIS: gravar humor cria .md, regenera cache,
    e a leitura subsequente do cache mostra a célula nova.
    """
    vault = _vault_sintetico(tmp_path)
    hoje = date.today()
    # Usa data dentro da janela de 90 dias para garantir que entra no cache.
    dia_alvo = hoje

    escrever_registro(
        vault,
        dia_alvo,
        humor=4,
        energia=3,
        ansiedade=2,
        foco=4,
        pessoa="pessoa_a",
        regenerar_cache=False,  # vamos chamar manualmente para isolar
    )

    saida = gerar_humor_heatmap(vault, periodo_dias=90, hoje=hoje)
    payload = json.loads(saida.read_text(encoding="utf-8"))
    autores = {(c["data"], c["autor"]) for c in payload.get("celulas", [])}
    assert (dia_alvo.isoformat(), "pessoa_a") in autores


# "Conhece-te a ti mesmo." -- Sócrates
