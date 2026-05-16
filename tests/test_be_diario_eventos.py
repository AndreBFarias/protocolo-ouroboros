"""Testes da Sprint UX-RD-18 -- Bem-estar / Diário emocional + Eventos.

Cobre:

  1.  ``be_diario._filtrar`` ordenação DESC + filtros modo/período/pessoa.
  2.  Filtro modo "trigger" / "vitoria" / "todos".
  3.  ``_card_html`` border-left correta (vermelha trigger / verde vitória).
  4.  Chips emoção renderizam (ou placeholder vazio quando ausentes).
  5.  ``escrever_diario`` grava .md válido e atualiza cache.
  6.  ``be_eventos`` timeline DESC.
  7.  ``_top_bairros`` agrega corretamente (top N por count, ASC alfa em empate).
  8.  ``escrever_evento`` grava .md válido e regenera cache.
  9.  Vault inexistente: páginas não crasham (fallback graceful via AppTest).
 10.  Contrato deep-link: tabs "Diário" e "Eventos" pertencem ao cluster Bem-estar.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from src.dashboard.paginas import be_diario, be_eventos
from src.mobile_cache.escrever_diario import escrever_diario
from src.mobile_cache.escrever_evento import escrever_evento

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE_VAULT = RAIZ / "tests" / "fixtures" / "vault_sintetico"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ler_frontmatter(arquivo: Path) -> dict:
    texto = arquivo.read_text(encoding="utf-8")
    assert texto.startswith("---\n"), "frontmatter ausente"
    bloco = texto.split("---", 2)[1]
    return yaml.safe_load(bloco) or {}


def _vault_sintetico_diario(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "inbox" / "mente" / "diario").mkdir(parents=True)
    return vault


def _vault_sintetico_eventos(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "eventos").mkdir(parents=True)
    return vault


# ===========================================================================
# 1. be_diario filtros + ordenação
# ===========================================================================


def test_be_diario_filtrar_ordena_desc_dentro_do_periodo():
    """Filtro respeita ordenação DESC e janela de período."""
    hoje = date(2026, 5, 5)
    items = [
        {
            "data": "2026-04-30",
            "autor": "pessoa_a",
            "modo": "trigger",
            "emocoes": [],
            "intensidade": 3,
            "com": [],
            "texto": "antigo",
        },
        {
            "data": "2026-05-04",
            "autor": "pessoa_b",
            "modo": "vitoria",
            "emocoes": [],
            "intensidade": 4,
            "com": [],
            "texto": "ontem",
        },
        {
            "data": "2025-01-01",
            "autor": "pessoa_a",
            "modo": "vitoria",
            "emocoes": [],
            "intensidade": 5,
            "com": [],
            "texto": "muito antigo",
        },
    ]
    # Dentro de 7 dias só os 2 primeiros entram.
    out = be_diario._filtrar(
        sorted(items, key=lambda i: i["data"], reverse=True),
        modo="todos",
        periodo_dias=7,
        pessoa="todos",
        hoje=hoje,
    )
    assert [i["data"] for i in out] == ["2026-05-04", "2026-04-30"], out


# ===========================================================================
# 2. Filtros modo/pessoa
# ===========================================================================


@pytest.mark.parametrize(
    "modo_filtro,esperado_count",
    [("todos", 2), ("trigger", 1), ("vitoria", 1)],
)
def test_be_diario_filtrar_modo(modo_filtro, esperado_count):
    hoje = date(2026, 5, 5)
    items = [
        {
            "data": "2026-05-04",
            "autor": "pessoa_a",
            "modo": "trigger",
            "emocoes": [],
            "intensidade": 2,
            "com": [],
            "texto": "x",
        },
        {
            "data": "2026-05-03",
            "autor": "pessoa_b",
            "modo": "vitoria",
            "emocoes": [],
            "intensidade": 4,
            "com": [],
            "texto": "y",
        },
    ]
    out = be_diario._filtrar(
        items,
        modo=modo_filtro,
        periodo_dias=30,
        pessoa="todos",
        hoje=hoje,
    )
    assert len(out) == esperado_count


def test_be_diario_filtrar_pessoa():
    hoje = date(2026, 5, 5)
    items = [
        {
            "data": "2026-05-04",
            "autor": "pessoa_a",
            "modo": "trigger",
            "emocoes": [],
            "intensidade": 2,
            "com": [],
            "texto": "x",
        },
        {
            "data": "2026-05-03",
            "autor": "pessoa_b",
            "modo": "vitoria",
            "emocoes": [],
            "intensidade": 4,
            "com": [],
            "texto": "y",
        },
    ]
    out = be_diario._filtrar(
        items,
        modo="todos",
        periodo_dias=30,
        pessoa="pessoa_a",
        hoje=hoje,
    )
    assert len(out) == 1 and out[0]["autor"] == "pessoa_a"


# ===========================================================================
# 3. Card HTML border-left
# ===========================================================================


def test_be_diario_card_border_trigger_vermelha():
    item = {
        "data": "2026-05-04",
        "autor": "pessoa_a",
        "modo": "trigger",
        "emocoes": ["ansiedade"],
        "intensidade": 3,
        "com": [],
        "texto": "ruim",
    }
    html = be_diario._card_html(item)
    # Cor token "negativo" do tema = #ff5555 (Dracula red).
    assert "border-left:4px solid #ff5555" in html
    assert "Trigger" in html
    assert "ansiedade" in html


def test_be_diario_card_border_vitoria_verde():
    item = {
        "data": "2026-05-04",
        "autor": "pessoa_b",
        "modo": "vitoria",
        "emocoes": ["alegria"],
        "intensidade": 5,
        "com": ["pessoa_a"],
        "texto": "consegui",
    }
    html = be_diario._card_html(item)
    assert "border-left:4px solid #50fa7b" in html
    assert "Vitória" in html


# ===========================================================================
# 4. Chips emoção + placeholder
# ===========================================================================


def test_be_diario_card_sem_emocoes_mostra_placeholder():
    item = {
        "data": "2026-05-04",
        "autor": "pessoa_a",
        "modo": "trigger",
        "emocoes": [],
        "intensidade": 1,
        "com": [],
        "texto": "",
    }
    html = be_diario._card_html(item)
    assert "sem emoções tagueadas" in html


# ===========================================================================
# 5. escrever_diario grava + regenera cache
# ===========================================================================


def test_escrever_diario_grava_md_e_regenera_cache(tmp_path: Path):
    vault = _vault_sintetico_diario(tmp_path)
    arquivo = escrever_diario(
        vault,
        date(2026, 5, 5),
        modo="trigger",
        emocoes=["ansiedade", "cansaço"],
        intensidade=3,
        com_quem=["pessoa_b"],
        frase="reuniao chata logo cedo",
        pessoa="pessoa_a",
    )

    assert arquivo.exists()
    assert arquivo.parent == vault / "inbox" / "mente" / "diario" / "2026-05-05"

    fm = _ler_frontmatter(arquivo)
    assert fm["tipo"] == "diario_emocional"
    assert fm["autor"] == "pessoa_a"
    assert fm["modo"] == "trigger"
    assert fm["intensidade"] == 3
    assert "ansiedade" in fm["emocoes"]
    assert "cansaço" in fm["emocoes"]

    cache_path = vault / ".ouroboros" / "cache" / "diario-emocional.json"
    assert cache_path.exists()
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "diario-emocional"
    assert any(it["modo"] == "trigger" for it in payload["items"])


def test_escrever_diario_modo_invalido():
    with pytest.raises(ValueError, match="modo inválido"):
        escrever_diario(
            Path("/tmp/x"),
            date(2026, 5, 5),
            modo="abacaxi",
            emocoes=[],
            intensidade=3,
            pessoa="pessoa_a",
            regenerar_cache=False,
        )


# ===========================================================================
# 6. be_eventos timeline DESC
# ===========================================================================


def test_be_eventos_filtrar_timeline_desc():
    hoje = date(2026, 5, 5)
    items = [
        {
            "data": "2026-04-29",
            "autor": "pessoa_a",
            "modo": "positivo",
            "lugar": "padaria",
            "bairro": "bela vista",
            "com": [],
            "categoria": "rolezinho",
            "fotos": [],
            "intensidade": 4,
        },
        {
            "data": "2026-05-02",
            "autor": "casal",
            "modo": "negativo",
            "lugar": "bar",
            "bairro": "centro",
            "com": [],
            "categoria": "jantar",
            "fotos": [],
            "intensidade": 2,
        },
    ]
    items_desc = sorted(items, key=lambda i: i["data"], reverse=True)
    out = be_eventos._filtrar(
        items_desc,
        modo="todos",
        periodo_dias=30,
        categoria="todas",
        pessoa="todos",
        hoje=hoje,
    )
    assert [i["data"] for i in out] == ["2026-05-02", "2026-04-29"]


# ===========================================================================
# 7. Top bairros agrega do cache (NÃO hardcoded)
# ===========================================================================


def test_be_eventos_top_bairros_agrega_count_e_ordena():
    items = [
        {"bairro": "centro"},
        {"bairro": "bela vista"},
        {"bairro": "centro"},
        {"bairro": ""},
        {"bairro": "asa norte"},
        {"bairro": "centro"},
    ]
    top = be_eventos._top_bairros(items, top_n=10)
    # centro=3, asa norte=1, bela vista=1. Empate desempata por nome ASC.
    assert top == [("centro", 3), ("asa norte", 1), ("bela vista", 1)]


def test_be_eventos_top_bairros_top_n_corta():
    items = [{"bairro": f"b{i}"} for i in range(20)]
    top = be_eventos._top_bairros(items, top_n=5)
    assert len(top) == 5


# ===========================================================================
# 8. escrever_evento grava + regenera cache
# ===========================================================================


def test_escrever_evento_grava_md_e_regenera_cache(tmp_path: Path):
    vault = _vault_sintetico_eventos(tmp_path)
    arquivo = escrever_evento(
        vault,
        date(2026, 5, 5),
        modo="positivo",
        lugar="padaria do bairro",
        bairro="bela vista",
        com_quem=["pessoa_b"],
        categoria="rolezinho",
        fotos=["foto.jpg"],
        intensidade=4,
        pessoa="casal",
        texto="cafe da manha sem pressa",
    )

    assert arquivo.exists()
    assert arquivo.parent == vault / "eventos" / "2026-05-05"

    fm = _ler_frontmatter(arquivo)
    assert fm["tipo"] == "evento"
    assert fm["modo"] == "positivo"
    assert fm["lugar"] == "padaria do bairro"
    assert fm["bairro"] == "bela vista"
    assert fm["intensidade"] == 4

    cache_path = vault / ".ouroboros" / "cache" / "eventos.json"
    assert cache_path.exists()
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "eventos"


def test_escrever_evento_modo_invalido():
    with pytest.raises(ValueError, match="modo inválido"):
        escrever_evento(
            Path("/tmp/x"),
            date(2026, 5, 5),
            modo="indiferente",
            lugar="x",
            pessoa="pessoa_a",
            regenerar_cache=False,
        )


def test_escrever_evento_intensidade_invalida():
    with pytest.raises(ValueError):
        escrever_evento(
            Path("/tmp/x"),
            date(2026, 5, 5),
            modo="positivo",
            lugar="x",
            intensidade=99,
            pessoa="pessoa_a",
            regenerar_cache=False,
        )


# ===========================================================================
# 9. Vault inexistente: páginas renderizam sem crash (AppTest)
# ===========================================================================


_SCRIPT_BE_DIARIO = """
import streamlit as st
from src.dashboard.paginas import be_diario

# Forçar vault None pelo monkey-patch local da função (a página chama
# descobrir_vault_root() em runtime; substituímos por lambda que retorna
# None para simular ambiente sem vault configurado).
be_diario.descobrir_vault_root = lambda: None
be_diario.renderizar({}, "30 dias", "pessoa_a", None)
"""

_SCRIPT_BE_EVENTOS = """
import streamlit as st
from src.dashboard.paginas import be_eventos

be_eventos.descobrir_vault_root = lambda: None
be_eventos.renderizar({}, "90 dias", "pessoa_a", None)
"""


def test_be_diario_renderiza_sem_crash_vault_ausente():
    """Sprint UX-M-02.D: warning agora vem como callout_html (markdown).

    Invariante: usuário continua vendo aviso de vault, mas via callout
    canônico (visualmente consistente com tema Dracula) em vez de
    ``st.warning`` (paleta amarelada default Streamlit).
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_SCRIPT_BE_DIARIO)
    at.run()
    assert not at.exception
    # Coleta avisos de qualquer canal: warning, info, ou markdown (callout).
    avisos = (
        [w.value for w in at.warning] + [i.value for i in at.info] + [m.value for m in at.markdown]
    )
    assert any(("vault" in str(t).lower() or "configure" in str(t).lower()) for t in avisos)


def test_be_eventos_renderiza_sem_crash_vault_ausente():
    """Sprint UX-M-02.D: warning agora vem como callout_html (markdown).

    Invariante: usuário continua vendo aviso de vault, mas via callout
    canônico (visualmente consistente com tema Dracula) em vez de
    ``st.warning`` (paleta amarelada default Streamlit).
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_SCRIPT_BE_EVENTOS)
    at.run()
    assert not at.exception
    avisos = (
        [w.value for w in at.warning] + [i.value for i in at.info] + [m.value for m in at.markdown]
    )
    assert any(("vault" in str(t).lower() or "configure" in str(t).lower()) for t in avisos)


# ===========================================================================
# 10. Contrato deep-link: tabs Diário/Eventos no cluster Bem-estar
# ===========================================================================


def test_deep_link_tabs_diario_e_eventos_no_cluster_bem_estar():
    """Deep-link ?cluster=Bem-estar&tab=Diário/Eventos depende da
    presença das duas abas em ABAS_POR_CLUSTER['Bem-estar']."""
    from src.dashboard.app import ABAS_POR_CLUSTER

    abas = ABAS_POR_CLUSTER["Bem-estar"]
    assert "Diário" in abas
    assert "Eventos" in abas


# "O que se nomeia, se atravessa." -- princípio terapêutico
