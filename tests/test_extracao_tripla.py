"""Testes da Sprint UX-RD-11 -- Extração Tripla.

Cobre:
  - Migração CSV idempotente (12 -> 13 colunas, no-op se já presente)
  - Schema CSV pós-migração inclui ``confianca_opus``
  - Helpers internos da página (badge formato, divergência, consenso)
  - Agrupamento por arquivo (status_global)
  - Stub legado ``validacao_arquivos`` ainda importável
  - Retrocompat: alias de aba legacy resolve para nome canônico novo
  - Mapa cluster cobre "Extração Tripla"
  - API pública ``extracao_tripla.renderizar`` existe com assinatura correta
  - Skill /validar-arquivo continua compatível (schema CSV não-quebrado)

Nenhum teste depende de Streamlit em runtime: páginas são importadas mas
``renderizar`` em si não é chamada (Streamlit só roda em servidor).
"""

from __future__ import annotations

import csv
import inspect
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.dashboard.componentes import drilldown
from src.dashboard.paginas import extracao_tripla, validacao_arquivos
from src.load import validacao_csv as vc

_RAIZ = Path(__file__).resolve().parents[1]
_SCRIPT_MIGRACAO = _RAIZ / "scripts" / "migrar_csv_confianca_opus.py"


# ----------------------------------------------------------------------------
# Schema do CSV
# ----------------------------------------------------------------------------


def test_schema_csv_inclui_confianca_opus():
    """Acceptance: CABECALHO canônico tem 13 colunas com confianca_opus."""
    assert "confianca_opus" in vc.CABECALHO
    assert len(vc.CABECALHO) == 13


def test_schema_csv_confianca_opus_apos_valor_opus():
    """confianca_opus deve vir imediatamente após valor_opus (semântico)."""
    idx_valor = vc.CABECALHO.index("valor_opus")
    idx_conf = vc.CABECALHO.index("confianca_opus")
    assert idx_conf == idx_valor + 1


def test_linha_validacao_default_confianca_opus_zero():
    """Default da dataclass é '0.0' para confianca_opus."""
    linha = vc.LinhaValidacao(
        sha8_arquivo="abc12345",
        tipo_arquivo="pdf",
        caminho_relativo="x.pdf",
        campo="valor",
    )
    assert linha.confianca_opus == "0.0"


# ----------------------------------------------------------------------------
# Migração idempotente
# ----------------------------------------------------------------------------


def _criar_csv_legado(tmp_path: Path) -> Path:
    """Cria CSV com schema antigo (12 colunas, sem confianca_opus)."""
    caminho = tmp_path / "validacao_legado.csv"
    cabecalho_antigo = [
        "sha8_arquivo",
        "tipo_arquivo",
        "caminho_relativo",
        "ts_processado",
        "campo",
        "valor_etl",
        "valor_opus",
        "valor_humano",
        "status_etl",
        "status_opus",
        "status_humano",
        "observacoes_humano",
    ]
    with caminho.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(cabecalho_antigo)
        writer.writerow(
            [
                "abc12345",
                "pdf",
                "x.pdf",
                "2026-05-04T10:00:00",
                "valor",
                "100.00",
                "100.00",
                "",
                "ok",
                "ok",
                "pendente",
                "",
            ]
        )
    return caminho


def test_migracao_dry_run_reporta_ausencia(tmp_path: Path):
    """Dry-run em CSV antigo reporta migração necessária e exit 0."""
    caminho = _criar_csv_legado(tmp_path)
    res = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT_MIGRACAO),
            "--dry-run",
            "--csv",
            str(caminho),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stderr
    assert "AUSENTE" in res.stdout
    # Não modificou o arquivo
    with caminho.open("r", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert "confianca_opus" not in header


def test_migracao_executar_adiciona_coluna(tmp_path: Path):
    """--executar transforma 12 -> 13 colunas e preenche default 0.0."""
    caminho = _criar_csv_legado(tmp_path)
    res = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT_MIGRACAO),
            "--executar",
            "--csv",
            str(caminho),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stderr
    with caminho.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        header = reader.fieldnames or []
    assert "confianca_opus" in header
    assert len(header) == 13
    # Default 0.0 aplicado
    assert all(r["confianca_opus"] == "0.0" for r in rows)


def test_migracao_idempotente(tmp_path: Path):
    """Rodar duas vezes não duplica coluna e reporta no-op."""
    caminho = _criar_csv_legado(tmp_path)
    subprocess.run(
        [sys.executable, str(_SCRIPT_MIGRACAO), "--executar", "--csv", str(caminho)],
        check=True,
        capture_output=True,
    )
    res = subprocess.run(
        [sys.executable, str(_SCRIPT_MIGRACAO), "--executar", "--csv", str(caminho)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    assert "no-op" in res.stdout.lower() or "PRESENTE" in res.stdout
    with caminho.open("r", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    # Apenas 1 ocorrência de confianca_opus, não 2
    assert header.count("confianca_opus") == 1


# ----------------------------------------------------------------------------
# Helpers internos da página
# ----------------------------------------------------------------------------


def test_detectar_divergencia_etl_opus_diferentes():
    linha = pd.Series({"valor_etl": "100.00", "valor_opus": "99.50"})
    assert extracao_tripla._detectar_divergencia(linha) is True


def test_detectar_divergencia_um_lado_vazio_nao_diverge():
    """ETL=100, Opus vazio -> não-divergente (não há comparação)."""
    linha = pd.Series({"valor_etl": "100.00", "valor_opus": ""})
    assert extracao_tripla._detectar_divergencia(linha) is False


def test_detectar_divergencia_consenso_nao_diverge():
    linha = pd.Series({"valor_etl": "100.00", "valor_opus": "100.00"})
    assert extracao_tripla._detectar_divergencia(linha) is False


def test_consenso_devolve_valor_quando_concordam():
    linha = pd.Series({"valor_etl": "42.00", "valor_opus": "42.00"})
    assert extracao_tripla._consenso(linha) == "42.00"


def test_consenso_vazio_quando_divergem():
    linha = pd.Series({"valor_etl": "42", "valor_opus": "43"})
    assert extracao_tripla._consenso(linha) == ""


def test_badge_formato_pdf():
    assert extracao_tripla._badge_formato("docs/x.pdf") == "PDF"


def test_badge_formato_imagem():
    assert extracao_tripla._badge_formato("foto.jpg") == "IMG"
    assert extracao_tripla._badge_formato("foto.PNG") == "IMG"


def test_badge_formato_csv_xlsx_ofx_html():
    assert extracao_tripla._badge_formato("a.csv") == "CSV"
    assert extracao_tripla._badge_formato("a.xlsx") == "XLSX"
    assert extracao_tripla._badge_formato("a.ofx") == "OFX"
    assert extracao_tripla._badge_formato("a.html") == "HTML"


def test_badge_formato_desconhecido():
    assert extracao_tripla._badge_formato("a.zzz") == "???"


def test_agrupar_por_arquivo_status_validado():
    """Status 'validado' quando todos status_humano in {ok, aprovado}."""
    df = pd.DataFrame(
        {
            "sha8_arquivo": ["a1", "a1"],
            "tipo_arquivo": ["pdf", "pdf"],
            "caminho_relativo": ["x.pdf", "x.pdf"],
            "campo": ["data", "valor"],
            "valor_etl": ["2026-01-01", "100"],
            "valor_opus": ["2026-01-01", "100"],
            "valor_humano": ["2026-01-01", "100"],
            "status_etl": ["ok", "ok"],
            "status_opus": ["ok", "ok"],
            "status_humano": ["ok", "ok"],
        }
    )
    grupos = extracao_tripla._agrupar_por_arquivo(df)
    assert len(grupos) == 1
    assert grupos.iloc[0]["status_global"] == "validado"


def test_agrupar_por_arquivo_status_conflito():
    """Status 'conflito' quando ETL≠Opus em algum campo e humano não-aprovou."""
    df = pd.DataFrame(
        {
            "sha8_arquivo": ["a1", "a1"],
            "tipo_arquivo": ["pdf", "pdf"],
            "caminho_relativo": ["x.pdf", "x.pdf"],
            "campo": ["data", "valor"],
            "valor_etl": ["2026-01-01", "100"],
            "valor_opus": ["2026-01-01", "99"],
            "valor_humano": ["", ""],
            "status_etl": ["ok", "ok"],
            "status_opus": ["ok", "ok"],
            "status_humano": ["pendente", "pendente"],
        }
    )
    grupos = extracao_tripla._agrupar_por_arquivo(df)
    assert grupos.iloc[0]["status_global"] == "conflito"


# ----------------------------------------------------------------------------
# Mascaramento de PII
# ----------------------------------------------------------------------------


def test_mascarar_pii_cpf():
    out = extracao_tripla._mascarar_pii("paguei pra 123.456.789-00 hoje")
    assert "123.456.789-00" not in out
    assert "XXX.XXX.XXX-XX" in out


def test_mascarar_pii_cnpj():
    out = extracao_tripla._mascarar_pii("CNPJ 12.345.678/0001-99")
    assert "12.345.678/0001-99" not in out
    assert "XX.XXX.XXX/XXXX-XX" in out


# ----------------------------------------------------------------------------
# API pública e estrutura
# ----------------------------------------------------------------------------


def test_api_publica_renderizar_existe():
    """Função renderizar(dados, mes, pessoa, ctx) existe."""
    sig = inspect.signature(extracao_tripla.renderizar)
    params = list(sig.parameters.keys())
    assert params == ["dados", "mes_selecionado", "pessoa", "ctx"]


def test_stub_validacao_arquivos_renderizar_existe():
    """Stub legado mantém renderizar() para retrocompat."""
    assert hasattr(validacao_arquivos, "renderizar")
    sig = inspect.signature(validacao_arquivos.renderizar)
    params = list(sig.parameters.keys())
    assert params == ["dados", "mes_selecionado", "pessoa", "ctx"]


# ----------------------------------------------------------------------------
# Roteamento de cluster e retrocompat de aba
# ----------------------------------------------------------------------------


def test_mapa_aba_inclui_extracao_tripla():
    assert drilldown.MAPA_ABA_PARA_CLUSTER["Extração Tripla"] == "Documentos"


def test_mapa_aba_nao_tem_mais_validacao_por_arquivo():
    """A chave canônica antiga foi substituída pela nova."""
    assert "Validação por Arquivo" not in drilldown.MAPA_ABA_PARA_CLUSTER


def test_aba_aliases_legacy_resolve_validacao_para_extracao():
    assert (
        drilldown.ABA_ALIASES_LEGACY["Validação por Arquivo"] == "Extração Tripla"
    )


def test_ler_filtros_da_url_resolve_alias_legacy(monkeypatch: pytest.MonkeyPatch):
    """?tab=Validação+por+Arquivo deve gravar 'Extração Tripla' em session."""

    class _FakeSt:
        def __init__(self, qp):
            self.session_state: dict = {}
            self.query_params = qp

    fake = _FakeSt({"tab": "Validação por Arquivo"})
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    drilldown.ler_filtros_da_url()
    assert (
        fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Extração Tripla"
    )
    # Cluster inferido também resolve para Documentos via mapa novo
    assert (
        fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Documentos"
    )


def test_ler_filtros_da_url_aceita_tab_extracao_tripla(
    monkeypatch: pytest.MonkeyPatch,
):
    """URL nova ?tab=Extração+Tripla resolve cluster=Documentos."""

    class _FakeSt:
        def __init__(self, qp):
            self.session_state: dict = {}
            self.query_params = qp

    fake = _FakeSt({"tab": "Extração Tripla"})
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    drilldown.ler_filtros_da_url()
    assert (
        fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Extração Tripla"
    )
    assert (
        fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Documentos"
    )


# ----------------------------------------------------------------------------
# Compat skill /validar-arquivo (assinatura preservada)
# ----------------------------------------------------------------------------


def test_atualizar_validacao_opus_assinatura_posicional_preservada(
    tmp_path: Path,
):
    """Skill /validar-arquivo chama (sha8, campo, valor, status, csv).

    A inclusão de confianca_opus NÃO pode quebrar essa assinatura
    posicional histórica. confianca_opus é keyword-only.
    """
    csv_path = tmp_path / "v.csv"
    arquivo = tmp_path / "x.pdf"
    arquivo.write_bytes(b"hello")
    vc.registrar_extracao(
        arquivo, tipo_arquivo="pdf", campos={"a": "1"}, caminho_csv=csv_path
    )
    sha8 = vc.calcular_sha8(arquivo)
    # Assinatura legacy: 5 posicionais
    ok = vc.atualizar_validacao_opus(sha8, "a", "1", "ok", csv_path)
    assert ok
    # Confiança preservada como default '0.0'
    linhas = vc.ler_csv(csv_path)
    assert linhas[0].confianca_opus == "0.0"


def test_atualizar_validacao_opus_aceita_confianca_opus_kwarg(tmp_path: Path):
    """Quem quiser registrar confianca_opus passa como keyword."""
    csv_path = tmp_path / "v.csv"
    arquivo = tmp_path / "x.pdf"
    arquivo.write_bytes(b"hello")
    vc.registrar_extracao(
        arquivo, tipo_arquivo="pdf", campos={"a": "1"}, caminho_csv=csv_path
    )
    sha8 = vc.calcular_sha8(arquivo)
    ok = vc.atualizar_validacao_opus(
        sha8, "a", "1", "ok", csv_path, confianca_opus=0.85
    )
    assert ok
    linhas = vc.ler_csv(csv_path)
    assert linhas[0].confianca_opus == "0.85"


# "Triangular três fontes é confessar com método." -- princípio operacional
