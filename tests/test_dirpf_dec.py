"""Testes do extrator DIRPF .DEC (P3.1 2026-04-23)."""

from __future__ import annotations

from pathlib import Path

from src.extractors.dirpf_dec import ExtratorDIRPFDec

HEADER_NORMAL = (
    "IRPF    202620253600105127373122   1999ANDRE DA SILVA BATISTA DE FARIAS"
    + " " * 30
    + "DF4108555002006011997N1N4210644911 LINUX\n"
)

HEADER_VITORIA = (
    "IRPF    202620253600107047532196   1999VITORIA MARIA SILVA DOS SANTOS"
    + " " * 30
    + "AL0000000000000000000N1N0000000000\n"
)


class TestExtratorDIRPF:
    def test_parse_cabecalho_retif(self, tmp_path: Path) -> None:
        arq = tmp_path / "05127373122-IRPF-A-2026-2025-RETIF.DEC"
        arq.write_text(HEADER_NORMAL, encoding="latin-1")
        ext = ExtratorDIRPFDec(arq)
        r = ext.extrair_dirpf(arq)
        d = r["documento"]
        assert d["cpf_declarante"] == "05127373122"
        assert d["razao_social"] == "ANDRE DA SILVA BATISTA DE FARIAS"
        assert d["ano_base"] == "2025"
        assert d["ano_exercicio"] == "2026"
        assert d["tipo_documento"] == "dirpf_retif"
        assert d["chave_44"].endswith("_RETIF")

    def test_parse_cabecalho_original_sem_retif(self, tmp_path: Path) -> None:
        arq = tmp_path / "05127373122-IRPF-A-2026-2025.DEC"
        arq.write_text(HEADER_NORMAL, encoding="latin-1")
        ext = ExtratorDIRPFDec(arq)
        r = ext.extrair_dirpf(arq)
        d = r["documento"]
        assert d["tipo_documento"] == "dirpf"
        assert not d["chave_44"].endswith("_RETIF")

    def test_parse_cabecalho_vitoria(self, tmp_path: Path) -> None:
        arq = tmp_path / "07047532196-IRPF-A-2026-2025.DEC"
        arq.write_text(HEADER_VITORIA, encoding="latin-1")
        ext = ExtratorDIRPFDec(arq)
        r = ext.extrair_dirpf(arq)
        d = r["documento"]
        assert d["cpf_declarante"] == "07047532196"
        assert "VITORIA" in d["razao_social"]

    def test_texto_sem_cabecalho_retorna_vazio(self, tmp_path: Path) -> None:
        arq = tmp_path / "ruim.dec"
        arq.write_text("TEXTO QUALQUER não DIRPF " * 10, encoding="latin-1")
        ext = ExtratorDIRPFDec(arq)
        r = ext.extrair_dirpf(arq)
        assert r["documento"] == {}

    def test_pode_processar_extensao_dec(self, tmp_path: Path) -> None:
        arq = tmp_path / "x.DEC"
        arq.write_text("x", encoding="latin-1")
        assert ExtratorDIRPFDec(arq).pode_processar(arq) is True

    def test_nao_processa_pdf(self, tmp_path: Path) -> None:
        arq = tmp_path / "x.pdf"
        arq.write_bytes(b"x")
        assert ExtratorDIRPFDec(arq).pode_processar(arq) is False
