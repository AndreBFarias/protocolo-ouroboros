"""Testes do componente preview_documento (Sprint 74)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.dashboard.componentes import preview_documento as pd


class TestTipoArquivo:
    def test_pdf(self) -> None:
        assert pd.tipo_arquivo(Path("foo.pdf")) == "pdf"
        assert pd.tipo_arquivo(Path("FOO.PDF")) == "pdf"

    def test_imagens_comuns(self) -> None:
        assert pd.tipo_arquivo(Path("a.png")) == "imagem"
        assert pd.tipo_arquivo(Path("a.jpg")) == "imagem"
        assert pd.tipo_arquivo(Path("a.jpeg")) == "imagem"
        assert pd.tipo_arquivo(Path("a.webp")) == "imagem"
        assert pd.tipo_arquivo(Path("a.gif")) == "imagem"

    def test_outro(self) -> None:
        assert pd.tipo_arquivo(Path("x.csv")) == "outro"
        assert pd.tipo_arquivo(Path("x.txt")) == "outro"
        assert pd.tipo_arquivo(Path("x.xml")) == "outro"

    def test_alias_privado_preserva_compat_spec(self) -> None:
        assert pd._tipo_arquivo(Path("foo.pdf")) == "pdf"


class TestIframeHtml:
    def test_contem_data_url_base64(self) -> None:
        html = pd._pdf_iframe_html("AAAA", 600)
        assert 'src="data:application/pdf;base64,AAAA"' in html
        assert 'height="600"' in html
        assert 'width="100%"' in html
        assert html.startswith("<iframe")
        assert html.endswith("</iframe>")

    def test_altura_configuravel(self) -> None:
        html = pd._pdf_iframe_html("X", 800)
        assert 'height="800"' in html


class TestLimites:
    def test_limite_bytes_documentado_5mb(self) -> None:
        assert pd.LIMITE_BYTES_EMBED == 5 * 1024 * 1024


class TestPreviewFallback:
    """Os fluxos que chamam Streamlit exigem st.* — testamos via mock leve."""

    def test_preview_arquivo_inexistente_nao_raise(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        chamadas: list[tuple[str, tuple]] = []

        class FakeSt:
            def error(self, *args):
                chamadas.append(("error", args))

            def warning(self, *args):
                chamadas.append(("warning", args))

            def info(self, *args):
                chamadas.append(("info", args))

            def markdown(self, *args, **kwargs):
                chamadas.append(("markdown", args))

            def image(self, *args, **kwargs):
                chamadas.append(("image", args))

            def download_button(self, *args, **kwargs):
                chamadas.append(("download_button", args))

        import sys

        monkeypatch.setitem(sys.modules, "streamlit", FakeSt())
        pd.preview_documento(tmp_path / "inexistente.pdf")
        assert chamadas and chamadas[0][0] == "error"

    def test_preview_imagem_chama_st_image(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        arquivo = tmp_path / "foto.png"
        arquivo.write_bytes(b"\x89PNG\r\n\x1a\n_fake")
        chamadas: list[str] = []

        class FakeSt:
            def error(self, *a):
                chamadas.append("error")

            def warning(self, *a):
                chamadas.append("warning")

            def info(self, *a):
                chamadas.append("info")

            def markdown(self, *a, **k):
                chamadas.append("markdown")

            def image(self, *a, **k):
                chamadas.append("image")

            def download_button(self, *a, **k):
                chamadas.append("download_button")

        import sys

        monkeypatch.setitem(sys.modules, "streamlit", FakeSt())
        pd.preview_documento(arquivo)
        assert "image" in chamadas

    def test_preview_pdf_grande_cai_em_download(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        arquivo = tmp_path / "gigante.pdf"
        # Cria arquivo acima do limite (5MB + 1 byte).
        arquivo.write_bytes(b"A" * (pd.LIMITE_BYTES_EMBED + 1))
        chamadas: list[str] = []

        class FakeSt:
            def error(self, *a):
                chamadas.append("error")

            def warning(self, *a):
                chamadas.append("warning")

            def info(self, *a):
                chamadas.append("info")

            def markdown(self, *a, **k):
                chamadas.append("markdown")

            def image(self, *a, **k):
                chamadas.append("image")

            def download_button(self, *a, **k):
                chamadas.append("download_button")

        import sys

        monkeypatch.setitem(sys.modules, "streamlit", FakeSt())
        pd.preview_documento(arquivo)
        assert "warning" in chamadas and "download_button" in chamadas
        assert "markdown" not in chamadas  # não embeda via iframe

    def test_preview_pdf_pequeno_embeda_via_markdown(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        arquivo = tmp_path / "pequeno.pdf"
        arquivo.write_bytes(b"%PDF-1.4\n")
        chamadas: list[str] = []

        class FakeSt:
            def error(self, *a):
                chamadas.append("error")

            def warning(self, *a):
                chamadas.append("warning")

            def info(self, *a):
                chamadas.append("info")

            def markdown(self, *a, **k):
                chamadas.append("markdown")

            def image(self, *a, **k):
                chamadas.append("image")

            def download_button(self, *a, **k):
                chamadas.append("download_button")

        import sys

        monkeypatch.setitem(sys.modules, "streamlit", FakeSt())
        pd.preview_documento(arquivo)
        assert "markdown" in chamadas
        assert "warning" not in chamadas

    def test_preview_outro_tipo_cai_em_info(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        arquivo = tmp_path / "qualquer.csv"
        arquivo.write_bytes(b"a,b,c\n1,2,3\n")
        chamadas: list[str] = []

        class FakeSt:
            def error(self, *a):
                chamadas.append("error")

            def warning(self, *a):
                chamadas.append("warning")

            def info(self, *a):
                chamadas.append("info")

            def markdown(self, *a, **k):
                chamadas.append("markdown")

            def image(self, *a, **k):
                chamadas.append("image")

            def download_button(self, *a, **k):
                chamadas.append("download_button")

        import sys

        monkeypatch.setitem(sys.modules, "streamlit", FakeSt())
        pd.preview_documento(arquivo)
        assert "info" in chamadas
        assert "download_button" in chamadas
