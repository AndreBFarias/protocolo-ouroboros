"""Testes do auditor estrutural do vault Ouroboros.

Sprint MOB-audit-estrutura-vault-md.

Cobertura mínima (>= 8 testes): 5 cenários OK + 5 quebrados via vault
sintético em ``tmp_path``. Adicionalmente, um teste regressivo confirma
que o mapping YAML continua alinhado com ``INBOX_SUBTIPOS`` do app
mobile (atalho leve: verificação por contagem + presença, não parse TS).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scripts.audit_vault_md import (
    AuditorVault,
    Relatorio,
    carregar_mapping,
    extrair_frontmatter,
    gerar_relatorio_md,
    main,
)

MAPPING_TESTE: dict[str, list[str]] = {
    "financeiro": ["pix", "extrato", "nota"],
    "saude": ["exame", "receita"],
    "casa": ["garantia", "contrato"],
    "outros": ["outro"],
}


def _md_canonico(
    *,
    subtipo: str = "pix",
    area: str = "financeiro",
    arquivo: str = "2026-05-12-153014-pix.jpg",
    schema_version: int = 1,
    tipo: str = "inbox_arquivo",
) -> str:
    """Frontmatter válido para um .md companion."""
    return textwrap.dedent(
        f"""\
        ---
        _schema_version: {schema_version}
        tipo: {tipo}
        subtipo: {subtipo}
        area: {area}
        arquivo: {arquivo}
        mime_type: image/jpeg
        tamanho_bytes: 142536
        origem: share_intent
        revisar: true
        ---

        Corpo livre.
        """
    )


def _criar_par_valido(
    tmp_path: Path,
    *,
    area: str = "financeiro",
    subtipo: str = "pix",
    basename: str = "2026-05-12-153014-pix",
    ext_binario: str = ".jpg",
) -> tuple[Path, Path]:
    pasta = tmp_path / "inbox" / area / subtipo
    pasta.mkdir(parents=True, exist_ok=True)
    md = pasta / f"{basename}.md"
    md.write_text(
        _md_canonico(
            area=area,
            subtipo=subtipo,
            arquivo=f"{basename}{ext_binario}",
        ),
        encoding="utf-8",
    )
    bin_path = pasta / f"{basename}{ext_binario}"
    bin_path.write_bytes(b"\x00" * 16)
    return md, bin_path


# ---------------------------------------------------------------------------
# Cenarios OK (5)
# ---------------------------------------------------------------------------


def test_vault_limpo_zero_violacoes(tmp_path: Path) -> None:
    _criar_par_valido(tmp_path)
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    assert relatorio.violacoes == []
    assert relatorio.total_arquivos == 2
    assert relatorio.total_binarios == 1
    assert relatorio.total_companions == 1


def test_par_em_cada_area_canonica_e_aceito(tmp_path: Path) -> None:
    _criar_par_valido(
        tmp_path,
        area="saude",
        subtipo="exame",
        basename="2026-05-12-090000-exame",
    )
    _criar_par_valido(
        tmp_path,
        area="casa",
        subtipo="garantia",
        basename="2026-05-12-090001-tv",
    )
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    assert relatorio.violacoes == []


def test_filename_sem_slug_e_aceito(tmp_path: Path) -> None:
    _criar_par_valido(
        tmp_path,
        basename="2026-05-12-153014",
        ext_binario=".pdf",
    )
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    assert relatorio.violacoes == []


def test_outros_aceita_sem_subpasta_de_subtipo(tmp_path: Path) -> None:
    """Area 'outros' aceita layout inbox/outros/<file> (espelha o app)."""
    pasta = tmp_path / "inbox" / "outros"
    pasta.mkdir(parents=True, exist_ok=True)
    basename = "2026-05-12-153014-misc"
    md = pasta / f"{basename}.md"
    md.write_text(
        _md_canonico(area="outros", subtipo="outro", arquivo=f"{basename}.pdf"),
        encoding="utf-8",
    )
    (pasta / f"{basename}.pdf").write_bytes(b"%PDF")
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    assert relatorio.violacoes == []


def test_exit_code_zero_em_vault_limpo(tmp_path: Path) -> None:
    _criar_par_valido(tmp_path)
    relatorio_md = tmp_path / "audit.md"
    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text(
        "financeiro: [pix, extrato, nota]\n"
        "saude: [exame, receita]\n"
        "casa: [garantia, contrato]\n"
        "outros: [outro]\n",
        encoding="utf-8",
    )
    exit_code = main(
        [
            "--vault-path",
            str(tmp_path),
            "--mapping",
            str(mapping_path),
            "--relatorio",
            str(relatorio_md),
        ]
    )
    assert exit_code == 0
    assert relatorio_md.exists()
    conteudo = relatorio_md.read_text(encoding="utf-8")
    assert "Total auditado: 2" in conteudo
    assert "Violações: 0" in conteudo


# ---------------------------------------------------------------------------
# Cenarios quebrados (5+)
# ---------------------------------------------------------------------------


def test_binario_solto_na_raiz_da_inbox_e_violacao(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "solto.jpg").write_bytes(b"\x00")
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    categorias = {v.categoria for v in relatorio.violacoes}
    assert "estrutura" in categorias
    assert any("solto na raiz" in v.detalhe for v in relatorio.violacoes)


def test_area_fora_do_mapping_e_violacao(tmp_path: Path) -> None:
    pasta = tmp_path / "inbox" / "mente" / "diario"
    pasta.mkdir(parents=True)
    (pasta / "2026-04-29-143000-vit.md").write_text(
        _md_canonico(area="mente", subtipo="diario"), encoding="utf-8"
    )
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    assert any(v.categoria == "estrutura" and "mente" in v.detalhe for v in relatorio.violacoes)


def test_filename_em_formato_brasileiro_e_violacao(tmp_path: Path) -> None:
    pasta = tmp_path / "inbox" / "financeiro" / "pix"
    pasta.mkdir(parents=True)
    (pasta / "12-05-2026.jpg").write_bytes(b"\x00")
    (pasta / "12-05-2026.md").write_text(_md_canonico(arquivo="12-05-2026.jpg"), encoding="utf-8")
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    violacoes_filename = [v for v in relatorio.violacoes if v.categoria == "filename"]
    assert violacoes_filename, "esperava violacao filename para 12-05-2026.jpg"


def test_frontmatter_sem_schema_version_e_violacao(tmp_path: Path) -> None:
    md, _ = _criar_par_valido(tmp_path)
    md.write_text(
        textwrap.dedent(
            """\
            ---
            tipo: inbox_arquivo
            subtipo: pix
            area: financeiro
            arquivo: 2026-05-12-153014-pix.jpg
            revisar: true
            ---
            """
        ),
        encoding="utf-8",
    )
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    assert any(
        v.categoria == "frontmatter" and "_schema_version" in v.detalhe for v in relatorio.violacoes
    )


def test_binario_sem_md_companion_e_violacao(tmp_path: Path) -> None:
    pasta = tmp_path / "inbox" / "financeiro" / "pix"
    pasta.mkdir(parents=True)
    (pasta / "2026-05-12-153014-pix.jpg").write_bytes(b"\x00")
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    assert any(
        v.categoria == "companion" and "sem .md companion" in v.detalhe for v in relatorio.violacoes
    )


def test_subtipo_fora_do_mapping_e_violacao(tmp_path: Path) -> None:
    pasta = tmp_path / "inbox" / "financeiro" / "boleto"
    pasta.mkdir(parents=True)
    (pasta / "2026-05-12-153014-bol.jpg").write_bytes(b"\x00")
    (pasta / "2026-05-12-153014-bol.md").write_text(
        _md_canonico(subtipo="boleto"), encoding="utf-8"
    )
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    assert any(v.categoria == "estrutura" and "boleto" in v.detalhe for v in relatorio.violacoes)


def test_schema_version_diferente_de_1_e_violacao(tmp_path: Path) -> None:
    md, _ = _criar_par_valido(tmp_path)
    md.write_text(_md_canonico(schema_version=2), encoding="utf-8")
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    assert any(
        v.categoria == "frontmatter" and "_schema_version=2" in v.detalhe
        for v in relatorio.violacoes
    )


# ---------------------------------------------------------------------------
# Regressivo: mapping YAML alinhado com app mobile
# ---------------------------------------------------------------------------


def test_areas_subtipos_alinhadas_com_app() -> None:
    """Garante que o YAML canônico não drifte do INBOX_SUBTIPOS do app.

    Atalho: verifica contagem (4 áreas, 8 subtipos) e presença dos rótulos.
    Quando o app adicionar novo subtipo, este teste falha e a sprint-filha
    é disparada.
    """
    raiz = Path(__file__).resolve().parents[1]
    mapping = carregar_mapping(raiz / "mappings" / "areas_subtipos.yaml")
    assert set(mapping.keys()) == {"financeiro", "saude", "casa", "outros"}
    total_subtipos = sum(len(v) for v in mapping.values())
    assert total_subtipos == 8, (
        f"esperava 8 subtipos canonicos (INBOX_SUBTIPOS), achou {total_subtipos}"
    )
    assert "pix" in mapping["financeiro"]
    assert "exame" in mapping["saude"]
    assert "garantia" in mapping["casa"]
    assert mapping["outros"] == ["outro"]


def test_extrair_frontmatter_retorna_none_quando_malformado() -> None:
    assert extrair_frontmatter("") is None
    assert extrair_frontmatter("sem frontmatter algum") is None
    assert extrair_frontmatter("---\nfrontmatter sem fechar\n# corpo") is None


def test_relatorio_md_lista_categorias_em_ordem(tmp_path: Path) -> None:
    relatorio = Relatorio(vault=tmp_path)
    relatorio.total_arquivos = 4
    relatorio.adicionar("estrutura", "x", "x violacao")
    relatorio.adicionar("filename", "y", "y violacao")
    saida = tmp_path / "audit.md"
    gerar_relatorio_md(relatorio, saida)
    texto = saida.read_text(encoding="utf-8")
    pos_estrutura = texto.find("Categoria 1")
    pos_filename = texto.find("Categoria 2")
    pos_frontmatter = texto.find("Categoria 3")
    pos_companion = texto.find("Categoria 4")
    assert 0 < pos_estrutura < pos_filename < pos_frontmatter < pos_companion


@pytest.mark.parametrize(
    "nome,valido",
    [
        ("2026-05-12-153014-pix.jpg", True),
        ("2026-05-12-153014.pdf", True),
        ("2026-05-12-153014-mercado-x.jpg", True),
        ("pix-2026-05-12.jpg", False),
        ("12-05-2026.jpg", False),
        ("pix.jpg", False),
    ],
)
def test_filename_regex_aceita_canonico_rejeita_outros(
    tmp_path: Path, nome: str, valido: bool
) -> None:
    pasta = tmp_path / "inbox" / "financeiro" / "pix"
    pasta.mkdir(parents=True)
    arq = pasta / nome
    arq.write_bytes(b"\x00")
    auditor = AuditorVault(tmp_path, MAPPING_TESTE)
    relatorio = auditor.executar()
    violacoes_filename = [v for v in relatorio.violacoes if v.categoria == "filename"]
    if valido:
        assert violacoes_filename == [] or all(arq.name not in v.path for v in violacoes_filename)
    else:
        assert any(arq.name in v.path for v in violacoes_filename)
