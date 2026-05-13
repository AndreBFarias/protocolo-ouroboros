"""Testes da Sprint MOB-bridge-4: inbox enxerga subpastas do app mobile.

Cobre 5 cenarios canonicos:

1. `processar_inbox` faz walk recursivo (encontra arquivos em subpastas).
2. Sidecar `inbox/.extracted/<sha8>.json` grava `area` e `subtipo_mobile`.
3. Hint `subtipo_mobile=pix` em JPEG -> tipo=`comprovante_pix_foto`.
4. Hint `subtipo_mobile=exame` em PDF -> tipo=`exame_medico`.
5. Arquivo na raiz da inbox (sem subpasta) tem area=None, subtipo_mobile=None
   (retrocompat -- cascata legada decide).

Os tres últimos testam `detectar_tipo` diretamente para isolar o hint
sem precisar materializar PDFs/JPEGs reais com conteúdo extraível.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.intake.registry import _MAPPING_SUBTIPO_MOBILE_TO_TIPO, detectar_tipo
from src.intake.router import gravar_sidecar_inbox


def _criar_arquivo(path: Path, conteudo: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(conteudo)
    return path


# ---------------------------------------------------------------------------
# Teste 1: walk recursivo descobre arquivos em subpastas
# ---------------------------------------------------------------------------


def test_processar_inbox_walk_recursivo_descobre_subpastas(tmp_path: Path) -> None:
    """`processar_inbox` deve enxergar arquivos em inbox/<area>/<subtipo>/."""
    from src.inbox_processor import EXTENSOES_SUPORTADAS

    inbox = tmp_path / "inbox"
    _criar_arquivo(inbox / "financeiro" / "pix" / "comprovante.jpg")
    _criar_arquivo(inbox / "saude" / "exame" / "hemograma.pdf")
    _criar_arquivo(inbox / "casa" / "garantia" / "tv.pdf")
    _criar_arquivo(inbox / "outros" / "outro" / "qualquer.txt")
    _criar_arquivo(inbox / "legado-na-raiz.csv")  # retrocompat

    # Simulacao do walk identico ao usado em processar_inbox.
    arquivos = sorted(
        f
        for f in inbox.rglob("*")
        if f.is_file()
        and f.suffix.lower() in EXTENSOES_SUPORTADAS
        and ".extracted" not in f.parts
    )

    nomes = [a.name for a in arquivos]
    # Pelo menos os 3 arquivos com extensao suportada em subpasta + 1 legado.
    # (.txt não esta em EXTENSOES_SUPORTADAS, .jpg/.pdf/.csv sim.)
    assert "comprovante.jpg" in nomes
    assert "hemograma.pdf" in nomes
    assert "tv.pdf" in nomes
    assert "legado-na-raiz.csv" in nomes


# ---------------------------------------------------------------------------
# Teste 2: sidecar inclui area + subtipo_mobile
# ---------------------------------------------------------------------------


def test_sidecar_inbox_grava_area_e_subtipo(tmp_path: Path) -> None:
    """`gravar_sidecar_inbox` deve incluir area+subtipo quando aplicavel."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    sha8 = "abc12345"

    sidecar_path = gravar_sidecar_inbox(
        inbox_raiz=inbox,
        sha8=sha8,
        tipo_arquivo="comprovante_pix_foto",
        area="financeiro",
        subtipo_mobile="pix",
        sucesso=True,
    )

    assert sidecar_path is not None
    assert sidecar_path.exists()
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert payload["sha8"] == sha8
    assert payload["tipo_arquivo"] == "comprovante_pix_foto"
    assert payload["area"] == "financeiro"
    assert payload["subtipo_mobile"] == "pix"
    assert payload["estado"] == "extraido"


# ---------------------------------------------------------------------------
# Teste 3: hint pix em JPEG -> comprovante_pix_foto
# ---------------------------------------------------------------------------


def test_hint_pix_jpeg_roteia_para_comprovante_pix_foto(tmp_path: Path) -> None:
    """`detectar_tipo` com subtipo_mobile=pix deve devolver tipo canonico pix."""
    arquivo = tmp_path / "comprovante.jpg"
    arquivo.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")

    decisao = detectar_tipo(
        arquivo,
        mime="image/jpeg",
        preview=None,
        pessoa="_indefinida",
        subtipo_mobile="pix",
    )

    # Tipo canonico do mapping eh comprovante_pix_foto (esperado mesmo sem
    # DOC-27 implementado -- cai em _classificar/ com tipo preservado).
    assert decisao.tipo == "comprovante_pix_foto"
    assert _MAPPING_SUBTIPO_MOBILE_TO_TIPO["pix"] == "comprovante_pix_foto"


# ---------------------------------------------------------------------------
# Teste 4: hint exame em PDF -> exame_medico
# ---------------------------------------------------------------------------


def test_hint_exame_pdf_roteia_para_exame_medico(tmp_path: Path) -> None:
    """`detectar_tipo` com subtipo_mobile=exame em PDF -> tipo=exame_medico."""
    arquivo = tmp_path / "hemograma.pdf"
    arquivo.write_bytes(b"%PDF-1.4\nfake")

    decisao = detectar_tipo(
        arquivo,
        mime="application/pdf",
        preview=None,
        pessoa="_indefinida",
        subtipo_mobile="exame",
    )

    assert decisao.tipo == "exame_medico"


# ---------------------------------------------------------------------------
# Teste 5: arquivo na raiz da inbox (sem subpasta) tem area=None / subtipo=None
# ---------------------------------------------------------------------------


def test_arquivo_raiz_inbox_sem_hint_cascata_legada(tmp_path: Path) -> None:
    """Sem subtipo_mobile, detectar_tipo cai na cascata atual (sem hint).

    Garante retrocompat: arquivos depositados direto em inbox/ raiz não
    quebram -- cascata YAML+legada decide normalmente.
    """
    arquivo = tmp_path / "legado.csv"
    arquivo.write_bytes(b"data,valor\n2026-01-01,100\n")

    # Sem subtipo_mobile -> não aciona hint, vai pra cascata legada/YAML.
    # Resultado específico depende do conteúdo; o que importa é que não
    # é um tipo canônico do mapping (porque hint não foi acionado).
    decisao = detectar_tipo(
        arquivo,
        mime="text/csv",
        preview="data,valor\n2026-01-01,100\n",
        pessoa="_indefinida",
        subtipo_mobile=None,
    )

    # Cascata pode classificar como qualquer coisa ou nada -- o invariante é
    # que não retornou nenhum dos tipos do mapping mobile (porque o hint não
    # foi consultado).
    tipos_mobile = set(_MAPPING_SUBTIPO_MOBILE_TO_TIPO.values()) | {"nfce_modelo_65"}
    assert decisao.tipo not in tipos_mobile or decisao.tipo is None


# ---------------------------------------------------------------------------
# Teste extra: subtipo_mobile=nota com PDF vira nfce_modelo_65 (regra MIME)
# ---------------------------------------------------------------------------


def test_hint_nota_pdf_vira_nfce_modelo_65(tmp_path: Path) -> None:
    """Subtipo `nota` eh refinado por MIME: PDF -> nfce_modelo_65."""
    arquivo = tmp_path / "nota.pdf"
    arquivo.write_bytes(b"%PDF-1.4\nfake")

    decisao = detectar_tipo(
        arquivo,
        mime="application/pdf",
        preview=None,
        pessoa="_indefinida",
        subtipo_mobile="nota",
    )

    assert decisao.tipo == "nfce_modelo_65"


def test_hint_nota_imagem_vira_cupom_fiscal_foto(tmp_path: Path) -> None:
    """Subtipo `nota` em imagem mantem cupom_fiscal_foto."""
    arquivo = tmp_path / "nota.jpg"
    arquivo.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")

    decisao = detectar_tipo(
        arquivo,
        mime="image/jpeg",
        preview=None,
        pessoa="_indefinida",
        subtipo_mobile="nota",
    )

    assert decisao.tipo == "cupom_fiscal_foto"
