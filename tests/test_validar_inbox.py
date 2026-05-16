"""Testes da Sprint VALIDAR-BATCH-01.

Cobre o script ``scripts/validar_inbox.py``: filtros por tipo/mês/divergência,
agrupamento por sha8, limite, progresso, comportamento com CSV vazio.
"""

from __future__ import annotations

import io
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

# Permite importar o script como módulo via sys.path
_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ_REPO / "scripts"))
sys.path.insert(0, str(_RAIZ_REPO))

import validar_inbox  # noqa: E402

from src.load import validacao_csv as vc  # noqa: E402

_TS = "2026-04-29T10:00:00"


def _criar_csv_com_pendencias(tmp_path: Path, registros: list[tuple]) -> Path:
    """Cria CSV de teste com lista de tuplas (sha8, tipo, campo, valor_etl,
    status_opus, ts, valor_humano)."""
    caminho = tmp_path / "validacao_arquivos.csv"
    linhas = []
    for sha8, tipo, campo, valor_etl, status_opus, ts, valor_humano in registros:
        linhas.append(
            vc.LinhaValidacao(
                sha8_arquivo=sha8,
                tipo_arquivo=tipo,
                caminho_relativo=f"data/raw/teste/{sha8}.pdf",
                campo=campo,
                valor_etl=valor_etl,
                status_etl="ok",
                ts_processado=ts,
                valor_opus="",
                status_opus=status_opus,
                valor_humano=valor_humano,
                status_humano="ok" if valor_humano else "pendente",
            )
        )
    vc.gravar_csv(linhas, caminho)
    return caminho


def _executar_cli(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Executa o CLI via subprocess e retorna (exit_code, stdout)."""
    cmd = [sys.executable, str(_RAIZ_REPO / "scripts" / "validar_inbox.py")] + args
    resultado = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or _RAIZ_REPO)
    return resultado.returncode, resultado.stdout


def test_filtro_tipo_seleciona_apenas_tipo_pedido(tmp_path, monkeypatch):
    """`--tipo X` filtra apenas linhas com aquele tipo_arquivo."""
    registros = [
        ("aaa11111", "nfce_modelo_65", "total", "100.00", "pendente", _TS, ""),
        ("bbb22222", "holerite_g4f", "salario_bruto", "5000.00", "pendente", _TS, ""),
        ("ccc33333", "nfce_modelo_65", "total", "200.00", "pendente", _TS, ""),
    ]
    caminho = _criar_csv_com_pendencias(tmp_path, registros)
    monkeypatch.setattr(vc, "_PATH_CSV_PADRAO", caminho)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        validar_inbox.comando_principal(
            type(
                "Args",
                (),
                {
                    "tipo": "nfce_modelo_65",
                    "mes": None,
                    "apenas_divergentes": False,
                    "limite": 50,
                },
            )()
        )
    saida = buffer.getvalue()
    assert "2 arquivo(s) pendente(s)" in saida
    assert "filtro: tipo=nfce_modelo_65" in saida
    assert "aaa11111" in saida
    assert "ccc33333" in saida
    assert "bbb22222" not in saida


def test_filtro_mes_extrai_de_ts_processado(tmp_path, monkeypatch):
    """`--mes YYYY-MM` filtra linhas cujo ts_processado começa com YYYY-MM."""
    registros = [
        ("aaa11111", "nfce_modelo_65", "total", "100.00", "pendente", "2026-04-15T10:00:00", ""),
        ("bbb22222", "nfce_modelo_65", "total", "200.00", "pendente", "2026-05-01T10:00:00", ""),
    ]
    caminho = _criar_csv_com_pendencias(tmp_path, registros)
    monkeypatch.setattr(vc, "_PATH_CSV_PADRAO", caminho)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        validar_inbox.comando_principal(
            type(
                "Args",
                (),
                {
                    "tipo": None,
                    "mes": "2026-04",
                    "apenas_divergentes": False,
                    "limite": 50,
                },
            )()
        )
    saida = buffer.getvalue()
    assert "1 arquivo(s) pendente(s)" in saida
    assert "aaa11111" in saida
    assert "bbb22222" not in saida


def test_apenas_divergentes_seleciona_arquivos_com_divergencia_humana(tmp_path, monkeypatch):
    """`--apenas-divergentes` filtra sha8 onde humano marcou valor != valor_etl."""
    registros = [
        # arquivo aaa: humano concorda (não-divergente)
        ("aaa11111", "nfce_modelo_65", "total", "100.00", "pendente", _TS, "100.00"),
        # arquivo bbb: humano discorda (divergente)
        ("bbb22222", "nfce_modelo_65", "total", "200.00", "pendente", _TS, "999.99"),
        # arquivo ccc: humano não preencheu (não-divergente, sem dado)
        ("ccc33333", "nfce_modelo_65", "total", "300.00", "pendente", _TS, ""),
    ]
    caminho = _criar_csv_com_pendencias(tmp_path, registros)
    monkeypatch.setattr(vc, "_PATH_CSV_PADRAO", caminho)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        validar_inbox.comando_principal(
            type(
                "Args",
                (),
                {
                    "tipo": None,
                    "mes": None,
                    "apenas_divergentes": True,
                    "limite": 50,
                },
            )()
        )
    saida = buffer.getvalue()
    assert "1 arquivo(s) pendente(s)" in saida
    assert "bbb22222" in saida
    assert "aaa11111" not in saida


def test_limite_respeitado(tmp_path, monkeypatch):
    """`--limite N` limita lista a N primeiros sha8."""
    registros = [
        (f"sha{i:05d}", "nfce_modelo_65", "total", f"{i * 10}.00", "pendente", _TS, "")
        for i in range(15)
    ]
    caminho = _criar_csv_com_pendencias(tmp_path, registros)
    monkeypatch.setattr(vc, "_PATH_CSV_PADRAO", caminho)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        validar_inbox.comando_principal(
            type(
                "Args",
                (),
                {
                    "tipo": None,
                    "mes": None,
                    "apenas_divergentes": False,
                    "limite": 5,
                },
            )()
        )
    saida = buffer.getvalue()
    # 5 arquivos listados (15 pendentes, limite 5)
    assert "5 arquivo(s) pendente(s)" in saida
    # primeiros 5 ordenados: sha00000..sha00004
    for i in range(5):
        assert f"sha{i:05d}" in saida
    # sha00005 em diante NÃO aparece
    assert "sha00005" not in saida


def test_agrupamento_por_sha8(tmp_path, monkeypatch):
    """1 arquivo com 5 campos pendentes vira 1 entrada (não 5)."""
    registros = [
        ("aaa11111", "holerite_g4f", "salario_bruto", "5000", "pendente", _TS, ""),
        ("aaa11111", "holerite_g4f", "inss", "550", "pendente", _TS, ""),
        ("aaa11111", "holerite_g4f", "irrf", "200", "pendente", _TS, ""),
        ("aaa11111", "holerite_g4f", "vr", "300", "pendente", _TS, ""),
        ("aaa11111", "holerite_g4f", "va", "400", "pendente", _TS, ""),
    ]
    caminho = _criar_csv_com_pendencias(tmp_path, registros)
    monkeypatch.setattr(vc, "_PATH_CSV_PADRAO", caminho)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        validar_inbox.comando_principal(
            type(
                "Args",
                (),
                {
                    "tipo": None,
                    "mes": None,
                    "apenas_divergentes": False,
                    "limite": 50,
                },
            )()
        )
    saida = buffer.getvalue()
    assert "1 arquivo(s) pendente(s)" in saida
    assert "campos pendentes (5)" in saida
    # todos os 5 campos listados na mesma entrada
    for campo in ("salario_bruto", "inss", "irrf", "vr", "va"):
        assert campo in saida


def test_csv_vazio_imprime_mensagem_e_sai_zero(tmp_path, monkeypatch):
    """CSV ausente ou sem pendências retorna 0 com mensagem amigável."""
    caminho_inexistente = tmp_path / "nao_existe.csv"
    monkeypatch.setattr(vc, "_PATH_CSV_PADRAO", caminho_inexistente)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        codigo = validar_inbox.comando_principal(
            type(
                "Args",
                (),
                {
                    "tipo": None,
                    "mes": None,
                    "apenas_divergentes": False,
                    "limite": 50,
                },
            )()
        )
    assert codigo == 0
    assert "sem pendencias" in buffer.getvalue()


def test_progresso_reportado_a_cada_5(tmp_path, monkeypatch):
    """Linha `=== progresso: N/M ===` aparece a cada 5 arquivos."""
    registros = [
        (
            f"s{i:07d}",
            "nfce_modelo_65",
            "total",
            f"{i * 10}.00",
            "pendente",
            "2026-04-29T10:00:00",
            "",
        )
        for i in range(12)
    ]
    caminho = _criar_csv_com_pendencias(tmp_path, registros)
    monkeypatch.setattr(vc, "_PATH_CSV_PADRAO", caminho)

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        validar_inbox.comando_principal(
            type(
                "Args",
                (),
                {
                    "tipo": None,
                    "mes": None,
                    "apenas_divergentes": False,
                    "limite": 50,
                },
            )()
        )
    saida = buffer.getvalue()
    # com 12 arquivos, progresso aparece em 5 e 10
    assert "progresso: 5/12" in saida
    assert "progresso: 10/12" in saida


@pytest.mark.parametrize("argumento", ["--help", "-h"])
def test_cli_help_funciona(argumento):
    """CLI imprime help válido com --help."""
    codigo, saida = _executar_cli([argumento])
    assert codigo == 0
    assert "validar_inbox" in saida or "VAL-BATCH" in saida or "filtra" in saida


# "Cada lote validado, cada divergencia exposta. Sem fila invisivel."
#  -- princípio operacional do Protocolo Ouroboros
