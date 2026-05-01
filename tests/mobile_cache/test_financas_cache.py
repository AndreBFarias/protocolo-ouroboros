"""Testes do gerador de cache financeiro semanal."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from src.mobile_cache.financas_cache import gerar_financas_cache


def _ler(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tx(
    *,
    data_obj: date,
    valor: float,
    categoria: str = "mercado",
    tipo: str = "Despesa",
    quem: str = "pessoa_a",
    local: str = "mercado luiza",
) -> dict:
    return {
        "data": data_obj,
        "valor": valor,
        "forma_pagamento": "Pix",
        "local": local,
        "quem": quem,
        "categoria": categoria,
        "classificacao": "Obrigatório",
        "banco_origem": "Itaú",
        "tipo": tipo,
        "mes_ref": data_obj.strftime("%Y-%m"),
        "tag_irpf": None,
        "obs": "",
        "identificador": f"id-{data_obj.isoformat()}-{valor}",
    }


def test_30_transacoes_em_4_semanas_gera_top_categorias_corretas(
    vault_temporario: Path,
    xlsx_factory,
) -> None:
    referencia = date(2026, 4, 29)  # quarta-feira
    inicio_semana = referencia - timedelta(days=referencia.weekday())  # segunda

    transacoes = []
    # Semana atual: 5 mercado (50 cada) + 2 transporte (30 cada) + 1 lazer (40)
    for i in range(5):
        transacoes.append(
            _tx(data_obj=inicio_semana + timedelta(days=i), valor=50.0, categoria="mercado")
        )
    transacoes.append(_tx(data_obj=inicio_semana, valor=30.0, categoria="transporte"))
    transacoes.append(
        _tx(data_obj=inicio_semana + timedelta(days=1), valor=30.0, categoria="transporte")
    )
    transacoes.append(_tx(data_obj=inicio_semana, valor=40.0, categoria="lazer"))
    # Semana anterior: 5 mercado (40 cada)
    for i in range(5):
        transacoes.append(
            _tx(data_obj=inicio_semana - timedelta(days=7 - i), valor=40.0, categoria="mercado")
        )

    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(
        vault_temporario,
        xlsx_path=xlsx,
        referencia=referencia,
    )
    payload = _ler(saida)

    assert payload["schema_version"] == 1
    # Gasto semana = 5*50 + 2*30 + 40 = 350
    assert payload["gasto_semana"] == 350.0
    # Gasto semana anterior = 5*40 = 200
    assert payload["gasto_semana_anterior"] == 200.0

    top = payload["top_categorias"]
    assert len(top) <= 5
    nomes = [c["nome"] for c in top]
    assert nomes[0] == "mercado"
    soma_pct = sum(c["percentual"] for c in top)
    assert 99.0 <= soma_pct <= 101.0


def test_delta_textual_acima_da_media(vault_temporario: Path, xlsx_factory) -> None:
    referencia = date(2026, 4, 29)
    inicio_semana = referencia - timedelta(days=referencia.weekday())
    transacoes = []
    # Semana atual: 1000
    transacoes.append(_tx(data_obj=inicio_semana, valor=1000.0, categoria="mercado"))
    # 12 semanas anteriores: 100 cada (media = 100)
    for offset in range(1, 13):
        transacoes.append(
            _tx(
                data_obj=inicio_semana - timedelta(days=7 * offset),
                valor=100.0,
                categoria="mercado",
            )
        )

    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(
        vault_temporario,
        xlsx_path=xlsx,
        referencia=referencia,
    )
    payload = _ler(saida)
    assert payload["delta_textual"] == "acima da media"


def test_delta_textual_abaixo_da_media(vault_temporario: Path, xlsx_factory) -> None:
    referencia = date(2026, 4, 29)
    inicio_semana = referencia - timedelta(days=referencia.weekday())
    transacoes = []
    transacoes.append(_tx(data_obj=inicio_semana, valor=10.0, categoria="mercado"))
    for offset in range(1, 13):
        transacoes.append(
            _tx(
                data_obj=inicio_semana - timedelta(days=7 * offset),
                valor=200.0,
                categoria="mercado",
            )
        )
    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    payload = _ler(saida)
    assert payload["delta_textual"] == "abaixo da media"


def test_delta_textual_dentro_da_media(vault_temporario: Path, xlsx_factory) -> None:
    referencia = date(2026, 4, 29)
    inicio_semana = referencia - timedelta(days=referencia.weekday())
    transacoes = []
    transacoes.append(_tx(data_obj=inicio_semana, valor=100.0, categoria="mercado"))
    for offset in range(1, 13):
        transacoes.append(
            _tx(
                data_obj=inicio_semana - timedelta(days=7 * offset),
                valor=100.0,
                categoria="mercado",
            )
        )
    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    payload = _ler(saida)
    assert payload["delta_textual"] == "dentro da media"


def test_sem_transacoes_na_semana_nao_lanca_excecao(
    vault_temporario: Path,
    xlsx_factory,
) -> None:
    referencia = date(2026, 4, 29)
    # Apenas transações em semana muito antiga.
    transacoes = [
        _tx(
            data_obj=referencia - timedelta(days=180),
            valor=50.0,
            categoria="mercado",
        )
    ]
    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    payload = _ler(saida)
    assert payload["gasto_semana"] == 0.0
    assert payload["top_categorias"] == []


def test_xlsx_inexistente_gera_payload_zerado(
    vault_temporario: Path,
    tmp_path: Path,
) -> None:
    referencia = date(2026, 4, 29)
    xlsx = tmp_path / "nao_existe.xlsx"
    saida = gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    payload = _ler(saida)
    assert payload["gasto_semana"] == 0.0
    assert payload["top_categorias"] == []
    assert payload["ultimas_transacoes"] == []
    assert payload["schema_version"] == 1


def test_ultimas_transacoes_ordenadas_desc_e_limitadas_a_20(
    vault_temporario: Path,
    xlsx_factory,
) -> None:
    referencia = date(2026, 4, 29)
    # 25 transações em datas variadas
    transacoes = []
    for i in range(25):
        transacoes.append(
            _tx(
                data_obj=referencia - timedelta(days=i),
                valor=10.0 + i,
                categoria="mercado",
            )
        )
    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    payload = _ler(saida)
    ultimas = payload["ultimas_transacoes"]
    assert len(ultimas) == 20
    datas = [u["data"] for u in ultimas]
    assert datas == sorted(datas, reverse=True)


def test_autor_em_transacoes_canonico_pessoa_ab_casal(
    vault_temporario: Path,
    xlsx_factory,
) -> None:
    referencia = date(2026, 4, 29)
    inicio_semana = referencia - timedelta(days=referencia.weekday())
    transacoes = [
        _tx(data_obj=inicio_semana, valor=10.0, quem="pessoa_a"),
        _tx(data_obj=inicio_semana, valor=20.0, quem="pessoa_b"),
        _tx(data_obj=inicio_semana, valor=30.0, quem="casal"),
        # Legado: nome real -> pessoa_id_de_legacy normaliza
        _tx(data_obj=inicio_semana, valor=40.0, quem="andre"),
    ]
    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    payload = _ler(saida)
    autores = {u["autor"] for u in payload["ultimas_transacoes"]}
    assert autores <= {"pessoa_a", "pessoa_b", "casal"}
    assert {"pessoa_a", "pessoa_b", "casal"} <= autores


def test_periodo_referencia_segunda_a_domingo(
    vault_temporario: Path,
    xlsx_factory,
) -> None:
    referencia = date(2026, 4, 29)  # quarta
    transacoes = [_tx(data_obj=referencia, valor=10.0)]
    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    payload = _ler(saida)
    # Semana de 2026-04-29 (quarta): segunda 2026-04-27, domingo 2026-05-03.
    assert payload["periodo_referencia"] == "2026-04-27 a 2026-05-03"


def test_idempotencia_payload_estavel_com_mesmo_gerado_em(
    vault_temporario: Path,
    xlsx_factory,
    gerado_em_referencia,
) -> None:
    referencia = date(2026, 4, 29)
    transacoes = [_tx(data_obj=referencia, valor=10.0)]
    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(
        vault_temporario,
        xlsx_path=xlsx,
        referencia=referencia,
        gerado_em=gerado_em_referencia,
    )
    bruto1 = saida.read_text(encoding="utf-8")
    saida2 = gerar_financas_cache(
        vault_temporario,
        xlsx_path=xlsx,
        referencia=referencia,
        gerado_em=gerado_em_referencia,
    )
    bruto2 = saida2.read_text(encoding="utf-8")
    assert bruto1 == bruto2


def test_apenas_despesa_e_imposto_entram_no_gasto(
    vault_temporario: Path,
    xlsx_factory,
) -> None:
    referencia = date(2026, 4, 29)
    inicio_semana = referencia - timedelta(days=referencia.weekday())
    transacoes = [
        _tx(data_obj=inicio_semana, valor=100.0, tipo="Despesa", categoria="mercado"),
        _tx(data_obj=inicio_semana, valor=50.0, tipo="Imposto", categoria="taxa"),
        _tx(
            data_obj=inicio_semana,
            valor=999.0,
            tipo="Receita",
            categoria="salario",
            quem="pessoa_a",
            local="empresa",
        ),
        _tx(
            data_obj=inicio_semana,
            valor=200.0,
            tipo="Transferência Interna",
            categoria="transferencia",
            quem="pessoa_a",
            local="entre contas",
        ),
    ]
    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    payload = _ler(saida)
    assert payload["gasto_semana"] == 150.0


def test_top_categorias_max_5_com_percentual_correto(
    vault_temporario: Path,
    xlsx_factory,
) -> None:
    referencia = date(2026, 4, 29)
    inicio_semana = referencia - timedelta(days=referencia.weekday())
    valores = [200.0, 150.0, 100.0, 80.0, 50.0, 20.0, 10.0]
    nomes = ["mercado", "transporte", "lazer", "saude", "moradia", "outros", "extras"]
    transacoes = [
        _tx(data_obj=inicio_semana, valor=v, categoria=n) for v, n in zip(valores, nomes)
    ]
    xlsx = xlsx_factory(transacoes)
    saida = gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    payload = _ler(saida)
    top = payload["top_categorias"]
    assert len(top) == 5
    assert [c["nome"] for c in top] == nomes[:5]
    total = sum(valores)
    assert abs(top[0]["percentual"] - 200.0 / total * 100) < 0.2


def test_atomic_write_invocado(
    vault_temporario: Path,
    xlsx_factory,
    monkeypatch,
) -> None:
    chamadas: list[tuple] = []

    import os as _os

    original = _os.replace

    def replace_spy(src, dst):
        chamadas.append((str(src), str(dst)))
        return original(src, dst)

    monkeypatch.setattr("src.mobile_cache.atomic.os.replace", replace_spy)
    referencia = date(2026, 4, 29)
    transacoes = [_tx(data_obj=referencia, valor=10.0)]
    xlsx = xlsx_factory(transacoes)
    gerar_financas_cache(vault_temporario, xlsx_path=xlsx, referencia=referencia)
    assert len(chamadas) == 1
    src_path, dst_path = chamadas[0]
    assert src_path.endswith(".tmp")
    assert dst_path.endswith("financas-cache.json")
