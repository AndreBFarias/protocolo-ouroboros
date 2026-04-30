"""Testes da Sprint VALIDAÇÃO-CSV-01.

Cobre o módulo ``src.load.validacao_csv``: schema, leitura, escrita
atômica, deduplicação por (sha8, campo), preservação de trabalho humano
em reextração, atualizações independentes de Opus e humano.
"""

from __future__ import annotations

import csv as csvlib
from pathlib import Path

import pytest

from src.load import validacao_csv as vc


def _tmp_csv(tmp_path: Path) -> Path:
    return tmp_path / "validacao.csv"


def test_calcular_sha8_arquivo_inexistente(tmp_path: Path):
    """Arquivo ausente devolve string vazia, sem levantar."""
    assert vc.calcular_sha8(tmp_path / "nao-existe.pdf") == ""


def test_calcular_sha8_consistente(tmp_path: Path):
    """Mesmo conteúdo gera mesmo sha8."""
    arquivo = tmp_path / "x.pdf"
    arquivo.write_bytes(b"abc 123")  # bytes ASCII puros
    assert vc.calcular_sha8(arquivo) == vc.calcular_sha8(arquivo)
    assert len(vc.calcular_sha8(arquivo)) == 8


def test_ler_csv_ausente_devolve_vazio(tmp_path: Path):
    """Arquivo ausente é tratado como CSV vazio, sem levantar."""
    assert vc.ler_csv(_tmp_csv(tmp_path)) == []


def test_registrar_extracao_cria_csv_com_cabecalho(tmp_path: Path):
    """Primeira extração cria CSV com cabeçalho canônico + 1 linha por campo."""
    arquivo = tmp_path / "doc.pdf"
    arquivo.write_bytes(b"x")
    csv_path = _tmp_csv(tmp_path)
    vc.registrar_extracao(
        arquivo=arquivo,
        tipo_arquivo="nfce_modelo_65",
        campos={"valor_total": "100.00", "cnpj_emissor": "00.776.574/0160-79"},
        caminho_csv=csv_path,
    )
    with csv_path.open(encoding="utf-8") as fh:
        reader = csvlib.DictReader(fh)
        assert reader.fieldnames == vc.CABECALHO
        linhas = list(reader)
    assert len(linhas) == 2
    campos = {linha["campo"] for linha in linhas}
    assert campos == {"valor_total", "cnpj_emissor"}


def test_registrar_extracao_idempotente_atualiza_etl(tmp_path: Path):
    """Re-registro da mesma chave (sha8, campo) atualiza valor_etl, não duplica."""
    arquivo = tmp_path / "doc.pdf"
    arquivo.write_bytes(b"x")
    csv_path = _tmp_csv(tmp_path)
    vc.registrar_extracao(
        arquivo=arquivo,
        tipo_arquivo="boleto_servico",
        campos={"valor_total": "50.00"},
        caminho_csv=csv_path,
    )
    vc.registrar_extracao(
        arquivo=arquivo,
        tipo_arquivo="boleto_servico",
        campos={"valor_total": "55.00"},  # valor revisto pelo extrator
        caminho_csv=csv_path,
    )
    linhas = vc.ler_csv(csv_path)
    assert len(linhas) == 1
    assert linhas[0].valor_etl == "55.00"


def test_atualizar_validacao_opus_preserva_etl(tmp_path: Path):
    """Marcar valor_opus não toca em valor_etl/status_etl/valor_humano."""
    arquivo = tmp_path / "h.pdf"
    arquivo.write_bytes(b"y")
    csv_path = _tmp_csv(tmp_path)
    vc.registrar_extracao(
        arquivo=arquivo,
        tipo_arquivo="holerite",
        campos={"salario_base": "5000.00"},
        caminho_csv=csv_path,
    )
    sha8 = vc.calcular_sha8(arquivo)
    ok = vc.atualizar_validacao_opus(
        sha8=sha8, campo="salario_base", valor_opus="5000,00", status_opus="ok",
        caminho_csv=csv_path,
    )
    assert ok is True
    linhas = vc.ler_csv(csv_path)
    assert len(linhas) == 1
    assert linhas[0].valor_etl == "5000.00"
    assert linhas[0].valor_opus == "5000,00"
    assert linhas[0].status_etl == "ok"
    assert linhas[0].status_opus == "ok"
    assert linhas[0].valor_humano == ""


def test_atualizar_validacao_humana_preserva_etl_e_opus(tmp_path: Path):
    """Marcação humana preserva ETL e Opus; observações vão para coluna própria."""
    arquivo = tmp_path / "h.pdf"
    arquivo.write_bytes(b"z")
    csv_path = _tmp_csv(tmp_path)
    vc.registrar_extracao(
        arquivo=arquivo,
        tipo_arquivo="holerite",
        campos={"inss": "440.00"},
        caminho_csv=csv_path,
    )
    sha8 = vc.calcular_sha8(arquivo)
    vc.atualizar_validacao_opus(sha8, "inss", "440,00", "ok", csv_path)
    ok = vc.atualizar_validacao_humana(
        sha8=sha8,
        campo="inss",
        valor_humano="440,00",
        status_humano="ok",
        observacoes="bate com contracheque",
        caminho_csv=csv_path,
    )
    assert ok is True
    linhas = vc.ler_csv(csv_path)
    assert linhas[0].valor_etl == "440.00"
    assert linhas[0].valor_opus == "440,00"
    assert linhas[0].valor_humano == "440,00"
    assert linhas[0].observacoes_humano == "bate com contracheque"


def test_re_registro_etl_preserva_trabalho_humano(tmp_path: Path):
    """Re-rodar pipeline (registrar_extracao 2x) NÃO sobrescreve valor_humano."""
    arquivo = tmp_path / "doc.pdf"
    arquivo.write_bytes(b"q")
    csv_path = _tmp_csv(tmp_path)
    vc.registrar_extracao(
        arquivo=arquivo,
        tipo_arquivo="nfce_modelo_65",
        campos={"valor_total": "100.00"},
        caminho_csv=csv_path,
    )
    sha8 = vc.calcular_sha8(arquivo)
    vc.atualizar_validacao_humana(
        sha8=sha8, campo="valor_total", valor_humano="100,00",
        status_humano="ok", observacoes="conferido", caminho_csv=csv_path,
    )
    # Re-extração com valor revisto pelo extrator
    vc.registrar_extracao(
        arquivo=arquivo,
        tipo_arquivo="nfce_modelo_65",
        campos={"valor_total": "100.50"},
        caminho_csv=csv_path,
    )
    linhas = vc.ler_csv(csv_path)
    assert linhas[0].valor_etl == "100.50"  # ETL atualizou
    assert linhas[0].valor_humano == "100,00"  # humano preservado
    assert linhas[0].observacoes_humano == "conferido"


def test_atualizar_opus_valida_status(tmp_path: Path):
    """Status fora do conjunto canônico levanta ValueError."""
    arquivo = tmp_path / "doc.pdf"
    arquivo.write_bytes(b"q")
    csv_path = _tmp_csv(tmp_path)
    vc.registrar_extracao(
        arquivo=arquivo, tipo_arquivo="x", campos={"a": "1"}, caminho_csv=csv_path
    )
    sha8 = vc.calcular_sha8(arquivo)
    with pytest.raises(ValueError):
        vc.atualizar_validacao_opus(sha8, "a", "1", "talvez", caminho_csv=csv_path)


def test_atualizar_em_chave_inexistente_retorna_false(tmp_path: Path):
    """Atualização sem ETL prévio retorna False (não cria linha nova)."""
    csv_path = _tmp_csv(tmp_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text("", encoding="utf-8")
    ok = vc.atualizar_validacao_opus(
        sha8="abcd1234", campo="x", valor_opus="y", caminho_csv=csv_path
    )
    assert ok is False


def test_filtrar_pendentes_opus(tmp_path: Path):
    """Filtro pega apenas linhas com status_opus=pendente."""
    arquivo = tmp_path / "doc.pdf"
    arquivo.write_bytes(b"r")
    csv_path = _tmp_csv(tmp_path)
    vc.registrar_extracao(
        arquivo=arquivo,
        tipo_arquivo="x",
        campos={"a": "1", "b": "2"},
        caminho_csv=csv_path,
    )
    sha8 = vc.calcular_sha8(arquivo)
    vc.atualizar_validacao_opus(sha8, "a", "1", "ok", csv_path)
    pendentes = vc.filtrar_pendentes_opus(caminho_csv=csv_path)
    assert len(pendentes) == 1
    assert pendentes[0].campo == "b"
