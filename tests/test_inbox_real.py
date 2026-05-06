"""Testes da Sprint UX-RD-15 -- Inbox real.

Cobre:
  1. ``listar_inbox()`` em diretório vazio.
  2. ``listar_inbox()`` lista arquivos com sha8 estável e estado correto.
  3. Sidecar ausente -> estado=aguardando.
  4. Sidecar com tipo -> estado=extraido.
  5. Sidecar com erro -> estado=falhou.
  6. Sidecar com duplicado_de -> estado=duplicado.
  7. ``contar_estados()`` soma == total.
  8. Dropzone aceita os 6+ formatos canônicos (PDF/CSV/XLSX/OFX/JPG/PNG).
  9. ``gravar_arquivo_inbox`` escreve em disco e resolve colisão por sha8.
 10. Skill-instr texto literal correto na página Inbox.
 11. Página inbox.renderizar é importável sem efeito colateral pesado.

Padrão Sprint UX-RD: testes não exigem dashboard rodando -- apenas
verificam contratos puros e shape de strings.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dashboard.paginas import inbox as pagina_inbox
from src.intake.inbox_reader import (
    EXTENSOES_ACEITAS,
    contar_estados,
    gravar_arquivo_inbox,
    listar_inbox,
)

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _gravar(arquivo: Path, conteudo: bytes = b"placeholder") -> None:
    arquivo.write_bytes(conteudo)


def _gravar_sidecar(diretorio: Path, sha8: str, payload: dict) -> Path:
    diretorio.mkdir(parents=True, exist_ok=True)
    destino = diretorio / f"{sha8}.json"
    destino.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return destino


# ----------------------------------------------------------------------------
# 1. Diretório vazio
# ----------------------------------------------------------------------------


def test_listar_inbox_diretorio_vazio_retorna_lista_vazia(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    assert listar_inbox(inbox) == []


def test_listar_inbox_diretorio_inexistente_retorna_lista_vazia(tmp_path: Path) -> None:
    inexistente = tmp_path / "inbox-que-nao-existe"
    assert listar_inbox(inexistente) == []


# ----------------------------------------------------------------------------
# 2. Lista arquivos com sha8 e estado
# ----------------------------------------------------------------------------


def test_listar_inbox_arquivos_basicos_tem_sha8_e_estado(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _gravar(inbox / "extrato.pdf", b"%PDF-1.4 placeholder de teste")
    _gravar(inbox / "fatura.csv", b"data,valor\n2026-01-01,10.00\n")

    itens = listar_inbox(inbox)
    assert len(itens) == 2

    for it in itens:
        assert "sha8" in it
        assert len(it["sha8"]) == 8
        assert it["estado"] == "aguardando"  # sem sidecar
        assert it["tipo"] in {"pdf", "csv"}
        assert it["filename"] in {"extrato.pdf", "fatura.csv"}
        assert it["sidecar"] is None
        assert it["tamanho_bytes"] > 0


def test_listar_inbox_ignora_arquivos_ocultos_e_nao_suportados(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _gravar(inbox / "valido.pdf", b"x")
    _gravar(inbox / ".oculto.pdf", b"x")
    _gravar(inbox / "sem_ext", b"x")
    _gravar(inbox / "binario.exe", b"x")

    itens = listar_inbox(inbox)
    nomes = {it["filename"] for it in itens}
    assert nomes == {"valido.pdf"}


# ----------------------------------------------------------------------------
# 3-6. Estados via sidecar
# ----------------------------------------------------------------------------


def test_sidecar_ausente_estado_aguardando(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _gravar(inbox / "novo.pdf", b"conteudo")

    [item] = listar_inbox(inbox)
    assert item["estado"] == "aguardando"
    assert item["sidecar"] is None


def test_sidecar_com_tipo_estado_extraido(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _gravar(inbox / "extrato.pdf", b"conteudo")
    [item] = listar_inbox(inbox)
    sha8 = item["sha8"]

    _gravar_sidecar(
        inbox / ".extracted",
        sha8,
        {"tipo_arquivo": "extrato_cc", "extrator": "nubank_cc", "transacoes": 47},
    )

    [item2] = listar_inbox(inbox)
    assert item2["estado"] == "extraido"
    assert item2["tipo_arquivo"] == "extrato_cc"
    assert item2["sidecar"]["transacoes"] == 47


def test_sidecar_com_erro_estado_falhou(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _gravar(inbox / "ruim.png", b"placeholder de imagem corrompida")
    [item] = listar_inbox(inbox)
    sha8 = item["sha8"]

    _gravar_sidecar(
        inbox / ".extracted",
        sha8,
        {"erro": "OCR não conseguiu ler valor total"},
    )

    [item2] = listar_inbox(inbox)
    assert item2["estado"] == "falhou"
    assert item2["erro"] == "OCR não conseguiu ler valor total"


def test_sidecar_com_duplicado_de_estado_duplicado(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _gravar(inbox / "copia.pdf", b"placeholder duplicado")
    [item] = listar_inbox(inbox)
    sha8 = item["sha8"]

    _gravar_sidecar(
        inbox / ".extracted",
        sha8,
        {"duplicado_de": "abc12345", "tipo_arquivo": "extrato_cc"},
    )

    [item2] = listar_inbox(inbox)
    assert item2["estado"] == "duplicado"
    assert item2["duplicado_de"] == "abc12345"


def test_sidecar_malformado_cai_para_aguardando(tmp_path: Path) -> None:
    """JSON inválido degrada graciosamente para aguardando."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _gravar(inbox / "x.pdf", b"x")
    [item] = listar_inbox(inbox)
    sha8 = item["sha8"]

    sidecar_dir = inbox / ".extracted"
    sidecar_dir.mkdir()
    (sidecar_dir / f"{sha8}.json").write_text("{ isto não é json válido", encoding="utf-8")

    [item2] = listar_inbox(inbox)
    assert item2["estado"] == "aguardando"
    assert item2["sidecar"] is None


# ----------------------------------------------------------------------------
# 7. contar_estados soma == total
# ----------------------------------------------------------------------------


def test_contar_estados_soma_igual_total(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    sidecar_dir = inbox / ".extracted"

    # 1 aguardando + 1 extraido + 1 falhou + 1 duplicado.
    _gravar(inbox / "a.pdf", b"a")  # aguardando
    _gravar(inbox / "b.pdf", b"bb")  # extraido
    _gravar(inbox / "c.pdf", b"ccc")  # falhou
    _gravar(inbox / "d.pdf", b"dddd")  # duplicado

    itens_seed = listar_inbox(inbox)
    sha_por_nome = {it["filename"]: it["sha8"] for it in itens_seed}

    _gravar_sidecar(sidecar_dir, sha_por_nome["b.pdf"], {"tipo_arquivo": "x"})
    _gravar_sidecar(sidecar_dir, sha_por_nome["c.pdf"], {"erro": "y"})
    _gravar_sidecar(
        sidecar_dir, sha_por_nome["d.pdf"], {"duplicado_de": sha_por_nome["a.pdf"]}
    )

    itens = listar_inbox(inbox)
    cont = contar_estados(itens)

    assert cont["aguardando"] == 1
    assert cont["extraido"] == 1
    assert cont["falhou"] == 1
    assert cont["duplicado"] == 1
    assert sum(cont.values()) == len(itens) == 4


# ----------------------------------------------------------------------------
# 8. Formatos aceitos (cobertura mínima 6: PDF/CSV/XLSX/OFX/JPG/PNG)
# ----------------------------------------------------------------------------


def test_extensoes_aceitas_cobre_seis_formatos_canonicos() -> None:
    obrigatorios = {".pdf", ".csv", ".xlsx", ".ofx", ".jpg", ".png"}
    assert obrigatorios.issubset(EXTENSOES_ACEITAS)


@pytest.mark.parametrize("ext", [".pdf", ".csv", ".xlsx", ".ofx", ".jpg", ".png"])
def test_dropzone_aceita_seis_formatos_canonicos(tmp_path: Path, ext: str) -> None:
    """Cada formato vira um item com tipo visual coerente."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _gravar(inbox / f"arquivo{ext}", b"placeholder de teste")
    [item] = listar_inbox(inbox)
    assert item["tipo"] in {"pdf", "csv", "xlsx", "ofx", "img"}


# ----------------------------------------------------------------------------
# 9. gravar_arquivo_inbox: escreve em disco, resolve colisão
# ----------------------------------------------------------------------------


def test_gravar_arquivo_inbox_escreve_em_disco(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    destino = gravar_arquivo_inbox(
        "novo.pdf", b"%PDF-1.4 placeholder", inbox_path=inbox
    )
    assert destino.exists()
    assert destino.read_bytes() == b"%PDF-1.4 placeholder"
    assert destino.parent == inbox


def test_gravar_arquivo_inbox_resolve_colisao_com_sha8(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    primeiro = gravar_arquivo_inbox("dup.pdf", b"v1", inbox_path=inbox)
    segundo = gravar_arquivo_inbox("dup.pdf", b"v2 diferente", inbox_path=inbox)

    assert primeiro != segundo
    assert primeiro.read_bytes() == b"v1"
    assert segundo.read_bytes() == b"v2 diferente"
    # Segundo arquivo recebeu prefixo sha8.
    assert segundo.name != "dup.pdf"
    assert segundo.name.endswith("_dup.pdf")


# ----------------------------------------------------------------------------
# 10. Skill-instr texto literal correto
# ----------------------------------------------------------------------------


def test_skill_instr_constantes_estao_corretas() -> None:
    assert pagina_inbox.SKILL_INSTR_TITULO == "Para extrair os arquivos pendentes"
    assert pagina_inbox.SKILL_INSTR_COMANDO == "/validar-arquivo"
    assert pagina_inbox.SKILL_INSTR_ADR == "ADR-13"


def test_skill_instr_html_contem_textos_canonicos() -> None:
    html = pagina_inbox._skill_instr_html()
    assert "Para extrair os arquivos pendentes" in html
    assert "/validar-arquivo" in html
    assert "ADR-13" in html
    assert 'class="skill-instr"' in html
    # Lição UX-RD-04: HTML deve estar minificado (uma linha só -- sem
    # newlines internos).
    assert "\n" not in html


# ----------------------------------------------------------------------------
# 11. Página importa sem efeito colateral
# ----------------------------------------------------------------------------


def test_pagina_inbox_expoe_renderizar() -> None:
    assert callable(pagina_inbox.renderizar)


def test_pagina_inbox_html_helpers_minificados() -> None:
    """Todos os geradores HTML respeitam lição UX-RD-04 (uma linha só)."""
    contagens = {"aguardando": 1, "extraido": 2, "falhou": 0, "duplicado": 0}
    for html in (
        pagina_inbox._page_header_html(3),
        pagina_inbox._barra_status_html(contagens, total=3),
        pagina_inbox._fila_vazia_html(),
        pagina_inbox._skill_instr_html(),
    ):
        assert "\n" not in html
        assert html.strip() == html


def test_fila_html_marca_arquivos_recentes_com_row_novo(tmp_path: Path) -> None:
    """Arquivo com mtime < 60s ganha classe row-novo (animação)."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _gravar(inbox / "fresco.pdf", b"x")  # mtime = agora
    itens = listar_inbox(inbox)
    html = pagina_inbox._fila_html(itens)
    assert "row-novo" in html


def test_fila_html_arquivo_antigo_sem_row_novo(tmp_path: Path) -> None:
    import os
    import time

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    arquivo = inbox / "antigo.pdf"
    _gravar(arquivo, b"x")
    # Backdate em 5 minutos.
    epoch_antigo = time.time() - 300
    os.utime(arquivo, (epoch_antigo, epoch_antigo))

    itens = listar_inbox(inbox)
    html = pagina_inbox._fila_html(itens)
    assert "row-novo" not in html


# "O caos organizado é o primeiro passo da ordem." -- princípio do GTD
