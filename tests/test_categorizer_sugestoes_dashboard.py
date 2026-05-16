"""Testes da página "Sugestor Outros".

Sprint CATEGORIZER-SUGESTAO-TFIDF (2026-05-16). Cobre helpers
puros: carregar JSON, filtros, promover para overrides.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.dashboard.paginas import categorizer_sugestoes as cs


def _payload_exemplo() -> dict:
    return {
        "gerado_em": "2026-05-16T22:00:00+00:00",
        "xlsx_origem": "data/output/ouroboros_2026.xlsx",
        "total_transacoes": 5840,
        "total_outros": 1031,
        "total_sugeridas": 863,
        "sugestoes": {
            "row_3": {
                "descricao": "Sushi Way Cn",
                "top1": "Sushi",
                "confianca_top1": 0.62,
                "sugestoes": [
                    {"categoria": "Sushi", "confianca": 0.62, "votos": 3},
                    {"categoria": "ALIMENTACAO", "confianca": 0.38, "votos": 2},
                ],
            },
            "row_5": {
                "descricao": "Pag*Bardoosvaldo",
                "top1": "Pets",
                "confianca_top1": 0.95,
                "sugestoes": [
                    {"categoria": "Pets", "confianca": 0.95, "votos": 5},
                ],
            },
            "row_9": {
                "descricao": "Posto Shell Asa Norte",
                "top1": "TRANSPORTE",
                "confianca_top1": 0.45,
                "sugestoes": [
                    {"categoria": "TRANSPORTE", "confianca": 0.45, "votos": 2},
                ],
            },
        },
    }


def test_carregar_sugestoes_devolve_lista_e_meta(tmp_path: Path) -> None:
    p = tmp_path / "sug.json"
    p.write_text(json.dumps(_payload_exemplo()), encoding="utf-8")
    lista, meta = cs._carregar_sugestoes(p)
    assert len(lista) == 3
    assert meta["total_outros"] == 1031
    assert meta["total_sugeridas"] == 863
    # Cada item tem campos canônicos:
    primeiro = lista[0]
    assert "id" in primeiro
    assert "descricao" in primeiro
    assert "top1" in primeiro
    assert "confianca_top1" in primeiro


def test_carregar_sugestoes_ausente_retorna_vazio(tmp_path: Path) -> None:
    lista, meta = cs._carregar_sugestoes(tmp_path / "nao_existe.json")
    assert lista == []
    assert meta == {}


def test_aplicar_filtros_confianca_minima(tmp_path: Path) -> None:
    p = tmp_path / "sug.json"
    p.write_text(json.dumps(_payload_exemplo()), encoding="utf-8")
    lista, _ = cs._carregar_sugestoes(p)
    alta = cs._aplicar_filtros(lista, confianca_minima=0.85, categorias_selecionadas=[])
    assert len(alta) == 1
    assert alta[0]["top1"] == "Pets"


def test_aplicar_filtros_categoria_top1(tmp_path: Path) -> None:
    p = tmp_path / "sug.json"
    p.write_text(json.dumps(_payload_exemplo()), encoding="utf-8")
    lista, _ = cs._carregar_sugestoes(p)
    transportes = cs._aplicar_filtros(
        lista, confianca_minima=0.0, categorias_selecionadas=["TRANSPORTE"]
    )
    assert len(transportes) == 1
    assert transportes[0]["descricao"].startswith("Posto Shell")


def test_promover_para_overrides_cria_arquivo(tmp_path: Path) -> None:
    yaml = tmp_path / "overrides.yaml"
    info = cs._promover_para_overrides(
        descricao="Sushi Way Cn",
        categoria="ALIMENTACAO",
        path_yaml=yaml,
    )
    assert info["match"] == "Sushi Way Cn"
    assert info["categoria"] == "ALIMENTACAO"
    conteudo = yaml.read_text(encoding="utf-8")
    assert "Sushi Way Cn" in conteudo
    assert "ALIMENTACAO" in conteudo
    assert "CATEGORIZER-SUGESTAO-TFIDF" in conteudo


def test_promover_para_overrides_apenda_em_existente(tmp_path: Path) -> None:
    yaml = tmp_path / "overrides.yaml"
    yaml.write_text("# overrides legados\n- match: x\n  categoria: A\n", encoding="utf-8")
    cs._promover_para_overrides("Novo", "B", path_yaml=yaml)
    conteudo = yaml.read_text(encoding="utf-8")
    assert "match: x" in conteudo  # preserva existente
    assert "Novo" in conteudo


# "Outros e debito; sugestor e juro pago." -- principio
