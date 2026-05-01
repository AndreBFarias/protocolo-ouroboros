"""Testes do gerador de cache do heatmap de humor."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from src.mobile_cache.humor_heatmap import gerar_humor_heatmap


def _ler(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_5_dailies_geram_5_celulas(
    vault_com_dailies: Path,
    hoje_referencia: date,
    gerado_em_referencia,
) -> None:
    saida = gerar_humor_heatmap(
        vault_com_dailies,
        periodo_dias=90,
        hoje=hoje_referencia,
        gerado_em=gerado_em_referencia,
    )

    payload = _ler(saida)
    assert payload["schema_version"] == 1
    assert payload["periodo_dias"] == 90
    assert isinstance(payload["celulas"], list)
    assert len(payload["celulas"]) == 5
    for celula in payload["celulas"]:
        assert celula["autor"] == "pessoa_a"
        assert isinstance(celula["humor"], int)


def test_frontmatter_incompleto_e_pulado_silenciosamente(
    vault_temporario: Path,
    hoje_referencia: date,
    daily_writer,
) -> None:
    daily_dir = vault_temporario / "daily"
    # Daily completo
    daily_writer(daily_dir, hoje_referencia, autor="pessoa_a", humor=4)
    # Daily sem campo obrigatório (humor ausente)
    nome = (hoje_referencia - timedelta(days=1)).isoformat() + ".md"
    (daily_dir / nome).write_text(
        "---\n"
        f"data: {(hoje_referencia - timedelta(days=1)).isoformat()}\n"
        "autor: pessoa_a\n"
        "energia: 3\n"
        "ansiedade: 2\n"
        "foco: 4\n"
        "---\n\nincompleto.\n",
        encoding="utf-8",
    )

    saida = gerar_humor_heatmap(
        vault_temporario,
        periodo_dias=90,
        hoje=hoje_referencia,
    )
    payload = _ler(saida)
    assert len(payload["celulas"]) == 1, "incompleto deve ser pulado"


def test_estatisticas_batem_com_calculo_manual(
    vault_temporario: Path,
    hoje_referencia: date,
    daily_writer,
) -> None:
    daily_dir = vault_temporario / "daily"
    # 3 dailies pessoa_a com humores 3, 4, 5 -> media = 4.0
    for i, h in enumerate([3, 4, 5]):
        daily_writer(daily_dir, hoje_referencia - timedelta(days=i), autor="pessoa_a", humor=h)
    # 2 dailies pessoa_b com humores 2, 4 -> media = 3.0
    for i, h in enumerate([2, 4]):
        daily_writer(
            daily_dir, hoje_referencia - timedelta(days=i + 5), autor="pessoa_b", humor=h
        )

    saida = gerar_humor_heatmap(
        vault_temporario,
        periodo_dias=90,
        hoje=hoje_referencia,
    )
    payload = _ler(saida)
    stats_a = payload["estatisticas"]["pessoa_a"]
    stats_b = payload["estatisticas"]["pessoa_b"]
    assert stats_a["registros_total"] == 3
    assert stats_a["registros_30d"] == 3
    assert stats_a["media_humor_30d"] == 4.0
    assert stats_b["registros_total"] == 2
    assert stats_b["media_humor_30d"] == 3.0


def test_periodo_dias_filtra_fora_do_intervalo(
    vault_temporario: Path,
    hoje_referencia: date,
    daily_writer,
) -> None:
    daily_dir = vault_temporario / "daily"
    daily_writer(daily_dir, hoje_referencia, autor="pessoa_a")
    daily_writer(daily_dir, hoje_referencia - timedelta(days=200), autor="pessoa_a")

    saida = gerar_humor_heatmap(
        vault_temporario,
        periodo_dias=90,
        hoje=hoje_referencia,
    )
    payload = _ler(saida)
    datas = {c["data"] for c in payload["celulas"]}
    assert hoje_referencia.isoformat() in datas
    assert (hoje_referencia - timedelta(days=200)).isoformat() not in datas


def test_schema_version_e_pessoas_canonicas(
    vault_com_dailies: Path,
    hoje_referencia: date,
) -> None:
    saida = gerar_humor_heatmap(
        vault_com_dailies,
        hoje=hoje_referencia,
    )
    payload = _ler(saida)
    assert payload["schema_version"] == 1
    assert payload["pessoas"] == ["pessoa_a", "pessoa_b"]
    # Estrutura de estatisticas para ambas as pessoas.
    for pessoa in ("pessoa_a", "pessoa_b"):
        stats = payload["estatisticas"][pessoa]
        assert set(stats.keys()) >= {"media_humor_30d", "registros_30d", "registros_total"}


def test_idempotencia_payload_byte_a_byte_exceto_gerado_em(
    vault_com_dailies: Path,
    hoje_referencia: date,
    gerado_em_referencia,
) -> None:
    saida = gerar_humor_heatmap(
        vault_com_dailies,
        hoje=hoje_referencia,
        gerado_em=gerado_em_referencia,
    )
    bruto1 = saida.read_text(encoding="utf-8")

    saida2 = gerar_humor_heatmap(
        vault_com_dailies,
        hoje=hoje_referencia,
        gerado_em=gerado_em_referencia,
    )
    bruto2 = saida2.read_text(encoding="utf-8")
    assert bruto1 == bruto2, "mesmo gerado_em + mesmo input -> mesmo arquivo"


def test_atomic_write_invoca_replace(
    vault_com_dailies: Path,
    hoje_referencia: date,
    monkeypatch,
) -> None:
    chamadas: list[tuple] = []

    import os as _os

    original = _os.replace

    def replace_spy(src, dst):
        chamadas.append((str(src), str(dst)))
        return original(src, dst)

    monkeypatch.setattr("src.mobile_cache.atomic.os.replace", replace_spy)
    gerar_humor_heatmap(vault_com_dailies, hoje=hoje_referencia)
    assert len(chamadas) == 1
    src_path, dst_path = chamadas[0]
    assert src_path.endswith(".tmp")
    assert dst_path.endswith("humor-heatmap.json")


def test_pessoa_b_so_no_inbox_humor(
    vault_temporario: Path,
    hoje_referencia: date,
    daily_writer,
) -> None:
    inbox_humor = vault_temporario / "inbox" / "mente" / "humor"
    daily_writer(inbox_humor, hoje_referencia, autor="pessoa_b", humor=5, foco=3)
    saida = gerar_humor_heatmap(
        vault_temporario,
        hoje=hoje_referencia,
    )
    payload = _ler(saida)
    autores = {c["autor"] for c in payload["celulas"]}
    assert autores == {"pessoa_b"}
    assert payload["estatisticas"]["pessoa_b"]["registros_total"] == 1


def test_autor_legado_andre_normalizado_para_pessoa_a(
    vault_temporario: Path,
    hoje_referencia: date,
    daily_writer,
) -> None:
    daily_writer(
        vault_temporario / "daily",
        hoje_referencia,
        autor="andre",
        humor=4,
    )
    saida = gerar_humor_heatmap(
        vault_temporario,
        hoje=hoje_referencia,
    )
    payload = _ler(saida)
    assert len(payload["celulas"]) == 1
    assert payload["celulas"][0]["autor"] == "pessoa_a"


def test_vault_vazio_gera_payload_valido(
    vault_temporario: Path,
    hoje_referencia: date,
) -> None:
    saida = gerar_humor_heatmap(
        vault_temporario,
        hoje=hoje_referencia,
    )
    payload = _ler(saida)
    assert payload["schema_version"] == 1
    assert payload["celulas"] == []
    for pessoa in ("pessoa_a", "pessoa_b"):
        assert payload["estatisticas"][pessoa]["registros_total"] == 0
        assert payload["estatisticas"][pessoa]["registros_30d"] == 0


def test_gerado_em_iso_8601_com_timezone_local(
    vault_com_dailies: Path,
    hoje_referencia: date,
) -> None:
    saida = gerar_humor_heatmap(
        vault_com_dailies,
        hoje=hoje_referencia,
    )
    payload = _ler(saida)
    gerado = payload["gerado_em"]
    # ISO 8601 com offset -03:00 (ou outro offset válido se TZ local mudar).
    assert "T" in gerado
    assert gerado.endswith("-03:00") or "+" in gerado.split("T")[-1] or "-" in gerado.split("T")[-1]


def test_dia_duplicado_em_daily_e_inbox_nao_duplica(
    vault_temporario: Path,
    hoje_referencia: date,
    daily_writer,
) -> None:
    daily_writer(vault_temporario / "daily", hoje_referencia, autor="pessoa_a", humor=4)
    daily_writer(
        vault_temporario / "inbox" / "mente" / "humor",
        hoje_referencia,
        autor="pessoa_a",
        humor=2,
    )
    saida = gerar_humor_heatmap(
        vault_temporario,
        hoje=hoje_referencia,
    )
    payload = _ler(saida)
    assert len(payload["celulas"]) == 1
    # Deve preservar o de daily/ (vem antes na ordem alfabética de diretórios).
    assert payload["celulas"][0]["humor"] == 4
