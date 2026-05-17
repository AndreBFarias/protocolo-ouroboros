"""Testes do script `scripts/detectar_tipos_novos.py`.

Sprint AUTO-TIPO-PROPOSTAS-DASHBOARD (2026-05-16). Cobre helpers
puros: tokenização, agrupamento, geração de propostas estruturadas.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "detectar_tipos_novos",
    Path(__file__).resolve().parents[1] / "scripts" / "detectar_tipos_novos.py",
)
assert _SPEC and _SPEC.loader
dtn = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dtn)


def test_tokens_nome_filtra_curtos_e_stopwords() -> None:
    """Tokens < 4 chars + stopwords são descartados."""
    tokens = dtn._tokens_nome("file_nfse_2024_documento_001.txt")
    assert "nfse" in tokens
    assert "documento" not in tokens  # stopword
    assert "file" not in tokens  # stopword
    assert "001" not in tokens  # tudo numérico


def test_tokens_conteudo_extrai_palavras() -> None:
    """Extração de tokens >= 4 chars do texto."""
    texto = "Nota Fiscal de Serviços Eletrônica NFS-e número 12345"
    tokens = dtn._tokens_conteudo(texto)
    assert "nota" in tokens
    assert "serviços" in tokens
    assert "nfs" not in tokens  # < 4 chars


def test_agrupar_arquivos_min_amostras(tmp_path: Path) -> None:
    """Grupo só se forma com ≥ min_amostras arquivos com token em comum."""
    p1 = tmp_path / "nfse_001.txt"
    p2 = tmp_path / "nfse_002.txt"
    p3 = tmp_path / "boleto_999.txt"
    for p in (p1, p2, p3):
        p.write_text("dummy", encoding="utf-8")
    grupos = dtn._agrupar_arquivos([p1, p2, p3], min_amostras=2)
    assert "nfse" in grupos
    assert len(grupos["nfse"]) == 2
    assert "boleto" not in grupos  # só 1 ocorrência


def test_gerar_propostas_diretorio_vazio_devolve_estrutura(monkeypatch, tmp_path: Path) -> None:
    """Diretório ausente/vazio → payload estrutural válido."""
    monkeypatch.setattr(dtn, "DIR_CLASSIFICAR", tmp_path / "nao_existe")
    payload = dtn.gerar_propostas()
    assert payload["total_arquivos_analisados"] == 0
    assert payload["propostas"] == []
    assert payload["arquivos_sem_grupo"] == []


def test_gerar_propostas_agrupa_amostras_reais(monkeypatch, tmp_path: Path) -> None:
    """Cria fixtures sintéticas e confirma proposta estruturada."""
    dir_class = tmp_path / "_classificar"
    dir_class.mkdir()
    (dir_class / "recibo_aluguel_001.txt").write_text("conteúdo a", encoding="utf-8")
    (dir_class / "recibo_aluguel_002.txt").write_text("conteúdo b", encoding="utf-8")
    (dir_class / "aluguel_xpto.txt").write_text("conteúdo c", encoding="utf-8")
    monkeypatch.setattr(dtn, "DIR_CLASSIFICAR", dir_class)
    payload = dtn.gerar_propostas(min_amostras=2)
    assert payload["total_arquivos_analisados"] == 3
    ids = {p["id_proposto"] for p in payload["propostas"]}
    # Os 3 arquivos compartilham token "aluguel"; 2 compartilham "recibo"
    assert "aluguel" in ids
    assert "recibo" in ids


def test_main_apply_grava_json(monkeypatch, tmp_path: Path) -> None:
    """`--apply` escreve JSON estruturado em PATH_PROPOSTAS."""
    dir_class = tmp_path / "_classificar"
    dir_class.mkdir()
    (dir_class / "nfse_001.txt").write_text("dummy", encoding="utf-8")
    (dir_class / "nfse_002.txt").write_text("dummy", encoding="utf-8")
    saida = tmp_path / "out.json"
    monkeypatch.setattr(dtn, "DIR_CLASSIFICAR", dir_class)
    monkeypatch.setattr(dtn, "PATH_PROPOSTAS", saida)

    rc = dtn.main(["--apply"])
    assert rc == 0
    assert saida.exists()
    d = json.loads(saida.read_text(encoding="utf-8"))
    assert d["total_arquivos_analisados"] == 2
    assert any(p["id_proposto"] == "nfse" for p in d["propostas"])


# "Toda regra começa como observação de padrão repetido." -- principio do indutor
