"""Testes das heurísticas puras (Sprint MOB-bridge-3).

Cada teste alimenta uma lista determinística de eventos e verifica
exatamente quais marcos a heurística devolve. Funções puras → sem
mocks de filesystem.
"""

from __future__ import annotations

from datetime import date, timedelta

from src.marcos_auto.heuristicas import (
    primeira_vitoria_da_semana,
    retorno_apos_hiato,
    sete_dias_humor,
    tres_treinos_em_sete_dias,
    trinta_dias_sem_trigger,
)


def _treino(data_str: str, autor: str = "pessoa_a") -> dict:
    return {"tipo": "treino_sessao", "data": data_str, "autor": autor}


def _humor(data_str: str, autor: str = "pessoa_a") -> dict:
    return {"tipo": "humor", "data": data_str, "autor": autor}


def _diario(data_str: str, modo: str, autor: str = "pessoa_a") -> dict:
    return {
        "tipo": "diario_emocional",
        "data": data_str,
        "autor": autor,
        "modo": modo,
    }


def _evento(data_str: str, modo: str, autor: str = "pessoa_a") -> dict:
    return {
        "tipo": "evento",
        "data": data_str,
        "autor": autor,
        "modo": modo,
    }


# ---------------- tres_treinos_em_sete_dias ----------------


def test_tres_treinos_dispara_no_terceiro_dentro_da_janela():
    eventos = [
        _treino("2026-04-23"),
        _treino("2026-04-25"),
        _treino("2026-04-28"),
    ]
    marcos = tres_treinos_em_sete_dias(eventos)
    assert len(marcos) == 1
    assert marcos[0]["data"] == "2026-04-28"
    assert marcos[0]["autor"] == "pessoa_a"
    assert marcos[0]["descricao"] == "Tres treinos nesta semana."
    assert "auto" in marcos[0]["tags"]
    assert "treino" in marcos[0]["tags"]


def test_tres_treinos_nao_dispara_se_so_dois():
    eventos = [_treino("2026-04-23"), _treino("2026-04-25")]
    assert tres_treinos_em_sete_dias(eventos) == []


def test_tres_treinos_so_emite_uma_vez_por_pessoa():
    eventos = [
        _treino("2026-04-23"),
        _treino("2026-04-25"),
        _treino("2026-04-28"),
        _treino("2026-04-30"),  # quarta janela rolling com 3 treinos
    ]
    marcos = tres_treinos_em_sete_dias(eventos)
    assert len(marcos) == 1


def test_tres_treinos_separa_por_pessoa():
    eventos = [
        _treino("2026-04-23", autor="pessoa_a"),
        _treino("2026-04-25", autor="pessoa_a"),
        _treino("2026-04-28", autor="pessoa_a"),
        _treino("2026-04-23", autor="pessoa_b"),
        _treino("2026-04-25", autor="pessoa_b"),
        _treino("2026-04-28", autor="pessoa_b"),
    ]
    marcos = tres_treinos_em_sete_dias(eventos)
    autores = {m["autor"] for m in marcos}
    assert autores == {"pessoa_a", "pessoa_b"}


# ---------------- retorno_apos_hiato ----------------


def test_retorno_apos_hiato_5_dias():
    eventos = [
        _treino("2026-04-20"),
        _treino("2026-04-25"),  # gap = 5 dias
    ]
    marcos = retorno_apos_hiato(eventos)
    assert len(marcos) == 1
    assert marcos[0]["data"] == "2026-04-25"
    assert "5 dias" in marcos[0]["descricao"]


def test_retorno_apos_hiato_nao_dispara_se_gap_4():
    eventos = [_treino("2026-04-20"), _treino("2026-04-24")]
    assert retorno_apos_hiato(eventos) == []


def test_retorno_apos_hiato_gap_grande_emite_dias_corretos():
    eventos = [_treino("2026-04-01"), _treino("2026-04-15")]  # gap 14
    marcos = retorno_apos_hiato(eventos)
    assert len(marcos) == 1
    assert "14 dias" in marcos[0]["descricao"]


# ---------------- sete_dias_humor ----------------


def test_sete_dias_humor_consecutivos():
    base = date(2026, 4, 1)
    eventos = [_humor((base + timedelta(days=i)).isoformat()) for i in range(7)]
    marcos = sete_dias_humor(eventos)
    assert len(marcos) == 1
    assert marcos[0]["data"] == "2026-04-07"
    assert marcos[0]["descricao"] == "Sete dias acompanhando."


def test_sete_dias_humor_quebra_se_falta_dia():
    eventos = [
        _humor("2026-04-01"),
        _humor("2026-04-02"),
        _humor("2026-04-03"),
        _humor("2026-04-05"),  # gap
        _humor("2026-04-06"),
        _humor("2026-04-07"),
        _humor("2026-04-08"),
    ]
    assert sete_dias_humor(eventos) == []


def test_sete_dias_humor_so_emite_uma_vez_por_autor():
    base = date(2026, 4, 1)
    eventos = [_humor((base + timedelta(days=i)).isoformat()) for i in range(14)]
    marcos = sete_dias_humor(eventos)
    assert len(marcos) == 1


# ---------------- trinta_dias_sem_trigger ----------------


def test_trinta_dias_sem_trigger_sem_nenhum_trigger():
    base = date(2026, 3, 1)
    eventos = [
        _diario(
            (base + timedelta(days=i)).isoformat() + "T10:00:00-03:00",
            modo="positivo",
        )
        for i in range(35)
    ]
    marcos = trinta_dias_sem_trigger(eventos)
    assert len(marcos) == 1
    assert marcos[0]["descricao"] == "Trinta dias sem registrar trigger."


def test_trinta_dias_sem_trigger_nao_dispara_se_apenas_15_dias():
    base = date(2026, 4, 1)
    eventos = [
        _diario(
            (base + timedelta(days=i)).isoformat() + "T10:00:00-03:00",
            modo="positivo",
        )
        for i in range(15)
    ]
    assert trinta_dias_sem_trigger(eventos) == []


def test_trinta_dias_sem_trigger_dispara_em_gap_entre_triggers():
    eventos = [
        _diario("2026-03-01T10:00:00-03:00", modo="trigger"),
        _diario("2026-04-05T10:00:00-03:00", modo="trigger"),  # gap = 35 dias
    ]
    marcos = trinta_dias_sem_trigger(eventos)
    assert len(marcos) == 1


# ---------------- primeira_vitoria_da_semana ----------------


def test_primeira_vitoria_uma_por_semana():
    eventos = [
        _evento("2026-04-01T10:00:00-03:00", modo="positivo"),
        _evento("2026-04-02T10:00:00-03:00", modo="positivo"),  # mesma semana ISO
        _diario("2026-04-08T10:00:00-03:00", modo="vitoria"),  # semana seguinte
    ]
    marcos = primeira_vitoria_da_semana(eventos)
    # 1 da semana 14, 1 da semana 15.
    datas = sorted(m["data"] for m in marcos)
    assert datas == ["2026-04-01", "2026-04-08"]


def test_primeira_vitoria_ignora_eventos_neutros():
    eventos = [
        _evento("2026-04-01T10:00:00-03:00", modo="negativo"),
        _diario("2026-04-02T10:00:00-03:00", modo="positivo"),
    ]
    assert primeira_vitoria_da_semana(eventos) == []


def test_primeira_vitoria_separa_por_pessoa():
    eventos = [
        _evento("2026-04-01T10:00:00-03:00", modo="positivo", autor="pessoa_a"),
        _evento("2026-04-02T10:00:00-03:00", modo="positivo", autor="pessoa_b"),
    ]
    marcos = primeira_vitoria_da_semana(eventos)
    assert len(marcos) == 2
    assert {m["autor"] for m in marcos} == {"pessoa_a", "pessoa_b"}


# "A clareza é a forma cortês da prova." -- Edsger Dijkstra
