"""Testes da página dashboard `src/dashboard/paginas/propostas_pendentes.py`.

Sprint META-PROPOSTAS-DASHBOARD-2026-05-15. Foco em: descoberta dinâmica
de propostas pendentes, KPI count correto, filtros tipo/idade, e
movimentação (aprovar/rejeitar) preservando o arquivo no destino.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.dashboard.paginas import propostas_pendentes


def _criar_proposta(
    diretorio: Path,
    categoria: str,
    proposta_id: str,
    status: str = "aberta",
    tipo: str | None = None,
    autor: str = "exemplo-agent",
    corpo: str = "Conteúdo da proposta.",
    dias_atras: int = 0,
) -> Path:
    """Cria proposta sintética com frontmatter mínimo + envelhece o mtime."""
    pasta = diretorio / categoria
    pasta.mkdir(parents=True, exist_ok=True)
    path = pasta / f"{proposta_id}.md"
    frontmatter = (
        "---\n"
        f"id: {proposta_id}\n"
        f"tipo: {tipo or categoria}\n"
        f"status: {status}\n"
        f"autor_proposta: {autor}\n"
        "---\n\n"
        f"{corpo}\n"
    )
    path.write_text(frontmatter, encoding="utf-8")
    if dias_atras > 0:
        alvo = (datetime.now(tz=timezone.utc) - timedelta(days=dias_atras)).timestamp()
        os.utime(path, (alvo, alvo))
    return path


def test_listar_pendentes_descobre_categorias_dinamicas(tmp_path: Path) -> None:
    """Pendentes são lidos de qualquer subpasta de propostas, sem hardcode."""
    base = tmp_path / "propostas"
    _criar_proposta(base, "categoria_item", "item-x")
    _criar_proposta(base, "linking", "link-y")
    _criar_proposta(base, "regra", "regra-z")
    # Categoria nova "extra_inventada" também deve ser descoberta.
    _criar_proposta(base, "extra_inventada", "novo-w")
    # Não-pendente fica de fora.
    _criar_proposta(base, "linking", "link-fechado", status="aprovada")
    # Pasta terminal _aprovadas com conteúdo é ignorada.
    _criar_proposta(base, "_aprovadas", "antiga-1")

    propostas = propostas_pendentes._listar_pendentes(base)
    ids = sorted(p.proposta_id for p in propostas)
    assert ids == ["item-x", "link-y", "novo-w", "regra-z"]


def test_contar_pendentes_alimenta_kpi(tmp_path: Path) -> None:
    """KPI count = número de arquivos com status: aberta nas categorias."""
    base = tmp_path / "propostas"
    _criar_proposta(base, "categoria_item", "alpha-1")
    _criar_proposta(base, "categoria_item", "alpha-2")
    _criar_proposta(base, "linking", "beta-1")
    _criar_proposta(base, "linking", "beta-2", status="rejeitada")  # não conta
    assert propostas_pendentes._contar_pendentes(base) == 3


def test_aprovar_move_para_aprovadas_data(tmp_path: Path) -> None:
    """Aprovar uma proposta a move para <categoria>/_aprovadas/<data>/."""
    base = tmp_path / "propostas"
    path = _criar_proposta(base, "categoria_item", "produto-novo")
    propostas = propostas_pendentes._listar_pendentes(base)
    assert len(propostas) == 1
    destino = propostas_pendentes._mover_para_destino(
        propostas[0], "aprovadas", data_iso="2026-05-15"
    )
    assert destino.exists()
    assert not path.exists()
    assert destino.parent.name == "2026-05-15"
    assert destino.parent.parent.name == "_aprovadas"
    # após mover, _contar_pendentes cai para 0.
    assert propostas_pendentes._contar_pendentes(base) == 0


def test_rejeitar_move_para_rejeitadas_data(tmp_path: Path) -> None:
    """Rejeitar move para <categoria>/_rejeitadas/<data>/, preservando arquivo."""
    base = tmp_path / "propostas"
    path = _criar_proposta(base, "linking", "conflito-007")
    propostas = propostas_pendentes._listar_pendentes(base)
    destino = propostas_pendentes._mover_para_destino(
        propostas[0], "rejeitadas", data_iso="2026-05-15"
    )
    assert destino.exists()
    assert not path.exists()
    assert destino.parent.parent.name == "_rejeitadas"
    # Conteúdo é preservado byte a byte.
    assert "conflito-007" in destino.read_text(encoding="utf-8")


def test_idade_em_dias_e_filtro_minimo(tmp_path: Path) -> None:
    """Idade derivada de mtime; filtro idade_minima descarta novos."""
    base = tmp_path / "propostas"
    _criar_proposta(base, "regra", "antiga", dias_atras=45)
    _criar_proposta(base, "regra", "intermediaria", dias_atras=15)
    _criar_proposta(base, "regra", "recente", dias_atras=2)
    propostas = propostas_pendentes._listar_pendentes(base)
    assert len(propostas) == 3
    # idade dias confere para a antiga (tolerância 1d para fuso/round).
    antiga = next(p for p in propostas if p.proposta_id == "antiga")
    assert antiga.idade_dias >= 44

    # filtro > 7d retém antiga + intermediaria, descarta recente.
    grandes = propostas_pendentes._aplicar_filtros(propostas, [], 8)
    ids = sorted(p.proposta_id for p in grandes)
    assert ids == ["antiga", "intermediaria"]

    # filtro tipo "regra" retém todas (todas pertencem à categoria).
    do_tipo = propostas_pendentes._aplicar_filtros(propostas, ["regra"], 0)
    assert len(do_tipo) == 3


def test_parser_strip_comentario_trailing(tmp_path: Path) -> None:
    """Frontmatter legado pode trazer ``tipo: x  # noqa: accent``; comentário
    é descartado para não vazar no título do expander."""
    pasta = tmp_path / "classificacao"
    pasta.mkdir()
    path = pasta / "antiga.md"
    path.write_text(
        "---\nid: antiga-x\ntipo: classificacao  # noqa: accent\nstatus: aberta\n---\n\nCorpo.\n",
        encoding="utf-8",
    )
    propostas = propostas_pendentes._listar_pendentes(tmp_path)
    assert len(propostas) == 1
    assert propostas[0].tipo == "classificacao"


def test_mover_para_destino_decisao_invalida_levanta(tmp_path: Path) -> None:
    """API defensiva contra typo: decisões válidas são apenas duas."""
    base = tmp_path / "propostas"
    _criar_proposta(base, "linking", "qualquer-x")
    propostas = propostas_pendentes._listar_pendentes(base)
    with pytest.raises(ValueError):
        propostas_pendentes._mover_para_destino(propostas[0], "deletadas")


# "Cada teste é uma promessa pequena ao futuro." -- princípio do regressivo
