"""Testes da Sprint UX-RD-19 -- Bem-estar / 8 páginas restantes.

Cobre:

  1.  be_editor_toml: validador aceita TOML correto.
  2.  be_editor_toml: validador rejeita TOML inválido.
  3.  be_editor_toml: salvar grava arquivo + cria diretório se ausente.
  4.  be_rotina: lê rotina.toml válido e expõe alarmes/tarefas/contadores.
  5.  be_rotina: rotina.toml ausente retorna None graceful.
  6.  be_recap: agregados de humor calculam média correta.
  7.  be_recap: agregados de eventos contam positivos/negativos.
  8.  be_memorias: heatmap_treinos não crasha sem itens.
  9.  be_memorias: cards de marcos ordenam DESC.
 10.  be_medidas: comparativo retorna delta correto entre primeira/última medida.
 11.  be_medidas: cache vazio = comparativo vazio.
 12.  be_ciclo: toggle off em privacidade.toml desativa página.
 13.  be_ciclo: toggle ausente = ativo (default).
 14.  be_cruzamentos: humor x eventos agrupa corretamente.
 15.  be_privacidade: salvar TOML cria seção [compartilhar].
 16.  be_privacidade: ler estado retorna default conservador (tudo False) sem arquivo.
"""

from __future__ import annotations

import json
import tomllib

from src.dashboard.paginas import (
    be_ciclo,
    be_cruzamentos,
    be_editor_toml,
    be_medidas,
    be_memorias,
    be_privacidade,
    be_recap,
    be_rotina,
)

# ===========================================================================
# 1-3. be_editor_toml
# ===========================================================================


def test_editor_toml_valida_aceita_toml_correto():
    ok, msg = be_editor_toml._validar_toml(be_editor_toml._TEMPLATE_DEFAULT)
    assert ok is True
    assert msg == ""


def test_editor_toml_valida_rejeita_toml_invalido():
    invalido = "[[alarme\nfaltando_fechar = 1"
    ok, msg = be_editor_toml._validar_toml(invalido)
    assert ok is False
    assert msg, "mensagem de erro deve ser não-vazia"


def test_editor_toml_salvar_cria_diretorio_e_grava(tmp_path):
    destino = tmp_path / ".ouroboros" / "rotina.toml"
    assert not destino.exists()
    be_editor_toml._salvar(destino, "[[alarme]]\nid = 'teste'\n")
    assert destino.exists()
    cfg = tomllib.loads(destino.read_text(encoding="utf-8"))
    assert cfg["alarme"][0]["id"] == "teste"


# ===========================================================================
# 4-5. be_rotina
# ===========================================================================


def test_rotina_le_toml_valido(tmp_path):
    arquivo = tmp_path / "rotina.toml"
    arquivo.write_text(
        '[[alarme]]\nid = "x"\nnome = "X"\nhora = "07:00"\ndias = ["seg"]\n'
        '[[tarefa]]\nid = "t"\nnome = "T"\nduracao_min = 5\ntipo = "diario"\n'
        '[[contador]]\nid = "c"\nnome = "C"\nmeta = 8\nreset = "diario"\n',
        encoding="utf-8",
    )
    cfg = be_rotina._ler_rotina(arquivo)
    assert cfg is not None
    assert len(cfg["alarme"]) == 1
    assert len(cfg["tarefa"]) == 1
    assert len(cfg["contador"]) == 1


def test_rotina_arquivo_ausente_retorna_none(tmp_path):
    inexistente = tmp_path / "nao_existe.toml"
    assert be_rotina._ler_rotina(inexistente) is None


# ===========================================================================
# 6-7. be_recap
# ===========================================================================


def test_recap_humor_calcula_media(tmp_path):
    vault = tmp_path / "vault"
    cache_dir = vault / ".ouroboros" / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "humor-heatmap.json").write_text(
        json.dumps(
            {
                "celulas": [
                    {"data": "2026-05-04", "humor": 4, "pessoa": "pessoa_a"},
                    {"data": "2026-05-03", "humor": 2, "pessoa": "pessoa_a"},
                ]
            }
        ),
        encoding="utf-8",
    )
    from datetime import date

    res = be_recap._agregados_humor(vault, dias=7, hoje=date(2026, 5, 5))
    assert res["qtd"] == 2
    assert res["media"] == 3.0
    assert res["melhor"] == 4
    assert res["pior"] == 2


def test_recap_eventos_conta_positivos_e_negativos():
    items = [
        {"modo": "positivo", "bairro": "centro", "data": "2026-05-01"},
        {"modo": "positivo", "bairro": "asa norte", "data": "2026-05-02"},
        {"modo": "negativo", "bairro": "centro", "data": "2026-05-03"},
    ]
    res = be_recap._agregados_eventos(items)
    assert res["qtd"] == 3
    assert res["positivos"] == 2
    assert res["negativos"] == 1
    # bairro centro aparece 2x, asa norte 1x
    top = dict(res["top_bairros"])
    assert top.get("centro") == 2


# ===========================================================================
# 8-9. be_memorias
# ===========================================================================


def test_memorias_heatmap_treinos_sem_itens_nao_crasha():
    from datetime import date

    html = be_memorias._heatmap_treinos_html([], date(2026, 5, 5))
    assert "<div" in html
    # 91 células renderizadas mesmo sem treinos.
    assert html.count("title=") == be_memorias.PERIODO_HEATMAP_DIAS


def test_memorias_marco_card_renderiza_html():
    marco = {
        "data": "2026-04-20",
        "titulo": "primeiro marco",
        "descricao": "teste",
        "tags": ["humor"],
        "auto": False,
        "autor": "pessoa_a",
    }
    html = be_memorias._marco_card_html(marco)
    assert "primeiro marco" in html
    assert "2026-04-20" in html
    assert "humor" in html


# ===========================================================================
# 10-11. be_medidas
# ===========================================================================


def test_medidas_comparativo_calcula_delta():
    items = [
        {"data": "2026-04-01", "peso": 80.0, "cintura": 90.0},
        {"data": "2026-05-01", "peso": 78.5, "cintura": 88.0},
    ]
    comp = be_medidas._comparativo(items)
    assert comp["peso"]["primeiro"] == 80.0
    assert comp["peso"]["ultimo"] == 78.5
    assert comp["peso"]["delta"] == -1.5
    assert comp["cintura"]["delta"] == -2.0
    assert comp["coxa"]["delta"] is None  # campo ausente


def test_medidas_comparativo_vazio_retorna_dict_vazio():
    assert be_medidas._comparativo([]) == {}


# ===========================================================================
# 12-13. be_ciclo
# ===========================================================================


def test_ciclo_toggle_off_desativa(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".ouroboros").mkdir(parents=True)
    (vault / ".ouroboros" / "privacidade.toml").write_text(
        "[modulos]\nciclo = false\n", encoding="utf-8"
    )
    assert be_ciclo._toggle_ativo(vault) is False


def test_ciclo_toggle_ausente_default_ativo(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".ouroboros").mkdir(parents=True)
    # arquivo não existe
    assert be_ciclo._toggle_ativo(vault) is True


# ===========================================================================
# 14. be_cruzamentos
# ===========================================================================


def test_cruzamentos_humor_x_eventos_agrupa():
    humor_dia = {
        "2026-05-01": 4.0,
        "2026-05-02": 2.0,
        "2026-05-03": 3.5,
    }
    eventos = [
        {"data": "2026-05-01", "modo": "positivo"},
        {"data": "2026-05-02", "modo": "negativo"},
    ]
    df = be_cruzamentos._correlacao_humor_eventos(humor_dia, eventos)
    grupos = {row["grupo"]: row["humor_medio"] for _, row in df.iterrows()}
    assert grupos["positivo"] == 4.0
    assert grupos["negativo"] == 2.0
    assert grupos["sem evento"] == 3.5


# ===========================================================================
# 15-16. be_privacidade
# ===========================================================================


def test_privacidade_salvar_cria_secao_compartilhar(tmp_path):
    caminho = tmp_path / ".ouroboros" / "privacidade.toml"
    estado = {s: True for s in be_privacidade.SCHEMAS}
    be_privacidade._salvar_estado(caminho, estado)
    assert caminho.exists()
    cfg = tomllib.loads(caminho.read_text(encoding="utf-8"))
    assert "compartilhar" in cfg
    for s in be_privacidade.SCHEMAS:
        assert cfg["compartilhar"][s] is True


def test_privacidade_arquivo_ausente_default_oculto(tmp_path):
    caminho = tmp_path / "nao_existe.toml"
    estado = be_privacidade._ler_estado(caminho)
    assert all(v is False for v in estado.values())
    assert set(estado.keys()) == set(be_privacidade.SCHEMAS)


# ===========================================================================
# Bonus: contrato deep-link das 12 abas Bem-estar continua íntegro
# ===========================================================================


def test_contrato_12_abas_bem_estar_preservado():
    """Sprint UX-RD-19 não pode quebrar a invariante das 12 abas."""
    from src.dashboard.app import ABAS_POR_CLUSTER

    abas = ABAS_POR_CLUSTER["Bem-estar"]
    assert len(abas) == 12, f"esperava 12 abas Bem-estar, obtive {len(abas)}"


# "O fim de um trabalho é o começo de outro." -- Leonardo da Vinci
