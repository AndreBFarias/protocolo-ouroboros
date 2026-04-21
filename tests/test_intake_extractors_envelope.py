"""Testes do src.intake.extractors_envelope.

Cobre:
- expandir_pdf_multipage com PDF real da inbox (pdf_notas.pdf, 3 páginas nativas)
  e PDF real de scan (notas de garantia e compras.pdf, 4 páginas só com imagem)
- diagnosticar_pagina classificando nativo vs scan corretamente nos 2 PDFs reais
- hash_identificador_natural detectando bilhete em cupom de garantia
- expandir_zip com defesas (zip-slip, zip-bomb, symlink, path absoluto)
- extrair_anexos_eml respeitando profundidade máxima
- cleanup_envelope removendo só em sucesso total

PDFs reais ficam em `inbox/`. Os testes NÃO alteram esses arquivos
(somente leitura). Saídas vão para tmp_path.
"""

from __future__ import annotations

import zipfile
from email.message import EmailMessage
from pathlib import Path

import pytest

from src.intake import extractors_envelope as env

INBOX = Path(__file__).resolve().parents[1] / "inbox"
PDF_NOTAS = INBOX / "pdf_notas.pdf"  # 3 pgs, texto NATIVO (com glyphs quebrados)
PDF_SCAN = INBOX / "notas de garantia e compras.pdf"  # 4 pgs, SCAN puro

SOMENTE_SE_INBOX_EXISTE = pytest.mark.skipif(
    not (PDF_NOTAS.exists() and PDF_SCAN.exists()),
    reason="PDFs reais da inbox/ não disponíveis (esperado em desenvolvimento local)",
)


@pytest.fixture(autouse=True)
def envelopes_em_tmp(tmp_path, monkeypatch):
    """Redireciona _ENVELOPES_BASE para tmp_path para isolamento entre testes."""
    monkeypatch.setattr(env, "_ENVELOPES_BASE", tmp_path / "_envelopes")
    yield


# ============================================================================
# expandir_pdf_multipage -- PDFs reais
# ============================================================================


@SOMENTE_SE_INBOX_EXISTE
def test_expandir_pdf_notas_gera_3_paginas_com_metadados():
    resultado = env.expandir_pdf_multipage(PDF_NOTAS)
    assert len(resultado.artefatos) == 3
    assert all(p.exists() and p.suffix == ".pdf" for p in resultado.artefatos)
    assert resultado.erros == []
    assert resultado.diretorio_envelope.name == resultado.sha8_envelope
    assert resultado.diretorio_envelope.parent.name == "pdf_split"
    # Diagnóstico no MESMO pass -- metadados completos por página
    assert len(resultado.paginas) == 3
    assert [p.indice for p in resultado.paginas] == [1, 2, 3]
    for p in resultado.paginas:
        assert p.diagnostico == "nativo"
        assert len(p.texto_nativo) > 100


@SOMENTE_SE_INBOX_EXISTE
def test_expandir_pdf_scan_gera_4_paginas_com_diagnostico_scan():
    resultado = env.expandir_pdf_multipage(PDF_SCAN)
    assert len(resultado.artefatos) == 4
    assert resultado.erros == []
    assert len(resultado.paginas) == 4
    for p in resultado.paginas:
        assert p.diagnostico == "scan"
        assert p.texto_nativo == ""


def test_expandir_pdf_inexistente_devolve_erros_sem_levantar(tmp_path):
    falso = tmp_path / "nao_existe.pdf"
    falso.write_bytes("%PDF-1.4 conteúdo inválido".encode("utf-8"))
    resultado = env.expandir_pdf_multipage(falso)
    assert resultado.artefatos == []
    assert len(resultado.erros) >= 1


# ============================================================================
# diagnosticar_pagina -- nativo vs scan nos PDFs reais
# ============================================================================


def test_diagnostico_threshold_customizavel(tmp_path, monkeypatch):
    """Threshold alto força página nativa a virar 'misto' QUANDO não há imagem grande.

    pdf_notas.pdf tem QR code grande na pg1 (cobre > 80% da área); sem
    o monkeypatch o teste cairia em 'scan'. Aqui o objetivo é testar
    o caminho threshold-alto-sem-imagem -> 'misto', que é o classificador
    do estado computado `_aguardando_revisao` da Sprint 41.
    """
    if not PDF_NOTAS.exists():
        pytest.skip("inbox indisponível")
    resultado = env.expandir_pdf_multipage(PDF_NOTAS)
    primeira = resultado.artefatos[0]
    monkeypatch.setattr(env, "_tem_imagem_grande", lambda _pagina: False)
    diagnostico, _ = env.diagnosticar_pagina(primeira, limite_chars=999_999)
    assert diagnostico == "misto"


# ============================================================================
# hash_identificador_natural
# ============================================================================


def test_hash_identificador_cupom_garantia_extrai_bilhete():
    texto = """
    DADOS DO SEGURO
    No DO BILHETE INDIVIDUAL: 781000129322124
    DATA DA EMISSAO: 19/04/2026
    """
    bilhete = env.hash_identificador_natural(texto, "cupom_garantia_estendida")
    assert bilhete == "781000129322124"


def test_hash_identificador_nfce_extrai_chave_44():
    texto = "5326 0400 7765 7401 8079 6530 4000 0432 8010 5868 2510"
    chave = env.hash_identificador_natural(texto, "nfce_consumidor_eletronica")
    assert chave == "53260400776574018079653040000432801058682510"


def test_hash_identificador_tipo_desconhecido_devolve_none():
    assert env.hash_identificador_natural("texto", "tipo_inexistente") is None


def test_hash_identificador_tipo_none_devolve_none():
    assert env.hash_identificador_natural("texto qualquer", None) is None


# ============================================================================
# expandir_zip -- defesas
# ============================================================================


def _criar_zip(path: Path, membros: list[tuple[str, bytes]]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for nome, conteudo in membros:
            zf.writestr(nome, conteudo)


def test_zip_normal_extrai_membros(tmp_path):
    zip_path = tmp_path / "ok.zip"
    _criar_zip(zip_path, [("a.pdf", b"pdf-bytes-a"), ("b.pdf", b"pdf-bytes-b")])
    resultado = env.expandir_zip(zip_path)
    assert len(resultado.artefatos) == 2
    assert resultado.erros == []
    assert all(p.exists() for p in resultado.artefatos)


def test_zip_recusa_path_absoluto(tmp_path):
    """zip-slip via path absoluto."""
    zip_path = tmp_path / "absoluto.zip"
    _criar_zip(zip_path, [("/etc/passwd_falso", b"x"), ("ok.pdf", b"pdf")])
    resultado = env.expandir_zip(zip_path)
    assert len(resultado.artefatos) == 1
    assert any("path absoluto" in e for e in resultado.erros)


def test_zip_recusa_path_com_dot_dot(tmp_path):
    """zip-slip via traversal."""
    zip_path = tmp_path / "traversal.zip"
    _criar_zip(zip_path, [("../escapou.pdf", b"x"), ("dentro.pdf", b"pdf")])
    resultado = env.expandir_zip(zip_path)
    assert len(resultado.artefatos) == 1
    assert any("zip-slip" in e for e in resultado.erros)


def test_zip_aborta_se_estoura_limite(tmp_path, monkeypatch):
    """Limite descompactado abortado no segundo membro (com tamanho declarado grande)."""
    monkeypatch.setattr(env, "LIMITE_DESCOMPACTADO_BYTES", 100)
    zip_path = tmp_path / "bomb.zip"
    _criar_zip(zip_path, [("a.bin", b"x" * 60), ("b.bin", b"y" * 60)])
    resultado = env.expandir_zip(zip_path)
    # Primeiro membro extraído (60 bytes); soma 120 > 100 aborta o segundo.
    assert len(resultado.artefatos) == 1
    assert any("limite descompactado excedido" in e for e in resultado.erros)


def test_zip_invalido_devolve_artefatos_vazio(tmp_path):
    falso = tmp_path / "falso.zip"
    falso.write_bytes("isso não é um zip".encode("utf-8"))
    resultado = env.expandir_zip(falso)
    assert resultado.artefatos == []
    assert len(resultado.erros) == 1


def test_zip_resolve_colisao_de_nome_em_subdiretorios(tmp_path):
    """ZIP bancário com janeiro/extrato.pdf + fevereiro/extrato.pdf:
    ambos viram artefatos distintos no _envelopes/<sha8>/."""
    zip_path = tmp_path / "bancos.zip"
    _criar_zip(
        zip_path,
        [
            ("janeiro/extrato.pdf", b"jan-bytes"),
            ("fevereiro/extrato.pdf", b"fev-bytes"),
            ("marco/extrato.pdf", b"mar-bytes"),
        ],
    )
    resultado = env.expandir_zip(zip_path)
    assert len(resultado.artefatos) == 3
    nomes = sorted(p.name for p in resultado.artefatos)
    assert nomes == ["extrato.pdf", "extrato_1.pdf", "extrato_2.pdf"]
    # Conteúdos preservados (ordem de extração estável dentro do zip)
    conteudos = sorted(p.read_bytes() for p in resultado.artefatos)
    assert conteudos == sorted([b"jan-bytes", b"fev-bytes", b"mar-bytes"])


# ============================================================================
# extrair_anexos_eml -- profundidade
# ============================================================================


def _criar_eml_simples(path: Path, anexos: list[tuple[str, bytes]]) -> None:
    msg = EmailMessage()
    msg["Subject"] = "teste"
    msg["From"] = "a@b.com"
    msg["To"] = "c@d.com"
    msg.set_content("corpo plano")
    for nome, conteudo in anexos:
        msg.add_attachment(conteudo, maintype="application", subtype="pdf", filename=nome)
    path.write_bytes(bytes(msg))


def test_eml_simples_extrai_anexos(tmp_path):
    eml_path = tmp_path / "carta.eml"
    _criar_eml_simples(eml_path, [("nota.pdf", b"pdf-bytes")])
    resultado = env.extrair_anexos_eml(eml_path)
    assert len(resultado.artefatos) == 1
    assert resultado.artefatos[0].name == "nota.pdf"
    assert resultado.artefatos[0].read_bytes() == b"pdf-bytes"


def _eml_com_anexo_pdf(subject: str, nome_pdf: str, conteudo_pdf: bytes) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "a@b.com"
    msg["To"] = "c@d.com"
    msg.set_content(f"corpo do {subject}")
    msg.add_attachment(conteudo_pdf, maintype="application", subtype="pdf", filename=nome_pdf)
    return msg


def _aninhar(msg_externa: EmailMessage, msg_interna: EmailMessage) -> None:
    """Anexa msg_interna como message/rfc822 dentro de msg_externa."""
    from email.mime.message import MIMEMessage

    msg_externa.attach(MIMEMessage(msg_interna))


def test_eml_aninhamento_excessivo_aborta(tmp_path):
    """4 níveis de message/rfc822 -- limite default 2 deve recusar o terceiro."""
    interior = _eml_com_anexo_pdf("nivel-mais-profundo", "deep.pdf", b"deep-pdf-bytes")
    nivel3 = _eml_com_anexo_pdf("nivel3", "n3.pdf", b"n3-bytes")
    _aninhar(nivel3, interior)
    nivel2 = _eml_com_anexo_pdf("nivel2", "n2.pdf", b"n2-bytes")
    _aninhar(nivel2, nivel3)
    raiz = _eml_com_anexo_pdf("raiz", "n1.pdf", b"n1-bytes")
    _aninhar(raiz, nivel2)

    eml_path = tmp_path / "aninhada.eml"
    eml_path.write_bytes(bytes(raiz))

    resultado = env.extrair_anexos_eml(eml_path, profundidade_max=2)
    # Anexos dos níveis 0, 1 e 2 são extraídos; do nível 3 (deep.pdf) NÃO
    nomes = {p.name for p in resultado.artefatos}
    assert "deep.pdf" not in nomes
    assert any("profundidade EML" in e for e in resultado.erros)


def test_eml_recusa_anexo_com_path_no_filename(tmp_path):
    """Filename com path traversal vira só basename."""
    msg = EmailMessage()
    msg["Subject"] = "x"
    msg.set_content("y")
    msg.add_attachment(b"x", maintype="application", subtype="pdf", filename="../../escapou.pdf")
    eml_path = tmp_path / "x.eml"
    eml_path.write_bytes(bytes(msg))
    resultado = env.extrair_anexos_eml(eml_path)
    assert len(resultado.artefatos) == 1
    assert resultado.artefatos[0].name == "escapou.pdf"
    assert ".." not in str(resultado.artefatos[0])


# ============================================================================
# cleanup_envelope
# ============================================================================


def test_cleanup_remove_quando_sucesso_total(tmp_path):
    diretorio = tmp_path / "_envelopes" / "pdf_split" / "abcdef01"
    diretorio.mkdir(parents=True)
    (diretorio / "pg1.pdf").write_bytes(b"x")
    removido = env.cleanup_envelope(diretorio, sucesso_total=True)
    assert removido is True
    assert not diretorio.exists()


def test_cleanup_mantem_quando_falha_parcial(tmp_path):
    diretorio = tmp_path / "_envelopes" / "pdf_split" / "abcdef02"
    diretorio.mkdir(parents=True)
    (diretorio / "pg1.pdf").write_bytes(b"x")
    removido = env.cleanup_envelope(diretorio, sucesso_total=False)
    assert removido is False
    assert diretorio.exists()


def test_cleanup_diretorio_inexistente_nao_levanta(tmp_path):
    inexistente = tmp_path / "nao_existe"
    assert env.cleanup_envelope(inexistente, sucesso_total=True) is False


# "Quem abre a caixa precisa estar pronto para o que sai dela." -- Pandora, paráfrase
