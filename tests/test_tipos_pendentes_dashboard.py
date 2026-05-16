"""Testes da página dashboard "Tipos por detectar".

Sprint AUTO-TIPO-PROPOSTAS-DASHBOARD (2026-05-16). Cobre helpers
puros (sem render Streamlit): leitura do JSON, filtros, aceitar,
rejeitar.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.dashboard.paginas import tipos_pendentes as tp


def _payload_exemplo() -> dict:
    return {
        "gerado_em": "2026-05-16T22:00:00+00:00",
        "total_arquivos_analisados": 5,
        "propostas": [
            {
                "id_proposto": "nfse_servico",
                "n_amostras": 3,
                "exemplos_sha256": ["abc123", "def456"],
                "exemplos_paths_relativos": [
                    "data/raw/_classificar/x.pdf",
                    "data/raw/_classificar/y.pdf",
                ],
                "regex_candidatos": ["NFS\\-e", "Documento\\sFiscal"],
                "mime_principal": "application/pdf",
                "extensao_principal": ".pdf",
                "confianca_global": 0.78,
            },
            {
                "id_proposto": "comprovante",
                "n_amostras": 2,
                "exemplos_sha256": ["111", "222"],
                "exemplos_paths_relativos": ["data/raw/_classificar/a.jpg"],
                "regex_candidatos": [],
                "mime_principal": "image/jpeg",
                "extensao_principal": ".jpg",
                "confianca_global": 0.4,
            },
        ],
        "arquivos_sem_grupo": ["data/raw/_classificar/orfao.png"],
    }


def test_carregar_propostas_devolve_lista_e_meta(tmp_path: Path) -> None:
    """JSON válido → propostas + metadata corretos."""
    p = tmp_path / "propostas_tipo_novo.json"
    p.write_text(json.dumps(_payload_exemplo()), encoding="utf-8")
    propostas, meta = tp._carregar_propostas(p)
    assert len(propostas) == 2
    assert propostas[0].id_proposto == "nfse_servico"
    assert propostas[0].confianca_global == 0.78
    assert meta["total_arquivos_analisados"] == 5
    assert meta["arquivos_sem_grupo"] == ["data/raw/_classificar/orfao.png"]


def test_carregar_propostas_ausente_retorna_vazio(tmp_path: Path) -> None:
    """JSON inexistente → ([], {}) sem crash."""
    propostas, meta = tp._carregar_propostas(tmp_path / "nao_existe.json")
    assert propostas == []
    assert meta == {}


def test_aplicar_filtros_por_extensao(tmp_path: Path) -> None:
    """Filtro de extensão respeita seleção do usuário."""
    p = tmp_path / "propostas.json"
    p.write_text(json.dumps(_payload_exemplo()), encoding="utf-8")
    propostas, _ = tp._carregar_propostas(p)
    so_pdf = tp._aplicar_filtros(propostas, [".pdf"], 0.0)
    assert len(so_pdf) == 1
    assert so_pdf[0].extensao_principal == ".pdf"


def test_aplicar_filtros_por_confianca_minima(tmp_path: Path) -> None:
    """Filtro de confiança mínima descarta propostas fracas."""
    p = tmp_path / "propostas.json"
    p.write_text(json.dumps(_payload_exemplo()), encoding="utf-8")
    propostas, _ = tp._carregar_propostas(p)
    alta = tp._aplicar_filtros(propostas, [], confianca_minima=0.6)
    assert len(alta) == 1
    assert alta[0].confianca_global >= 0.6


def test_rejeitar_proposta_apenda_no_json(tmp_path: Path) -> None:
    """Rejeição grava entry em propostas_tipo_rejeitadas.json."""
    proposta = tp.PropostaTipo(
        id_proposto="x",
        n_amostras=2,
        exemplos_sha256=[],
        exemplos_paths=[],
        regex_candidatos=[],
        mime_principal="application/pdf",
        extensao_principal=".pdf",
        confianca_global=0.3,
    )
    dest = tmp_path / "rejeitadas.json"
    tp._rejeitar_proposta(proposta, dest)
    d = json.loads(dest.read_text(encoding="utf-8"))
    assert len(d["rejeitadas"]) == 1
    assert d["rejeitadas"][0]["id_proposto"] == "x"
    # Segunda rejeição apenda (não substitui):
    tp._rejeitar_proposta(proposta, dest)
    d2 = json.loads(dest.read_text(encoding="utf-8"))
    assert len(d2["rejeitadas"]) == 2


def test_aceitar_proposta_apenda_yaml(tmp_path: Path) -> None:
    """Aceite cria/apenda entry em tipos_documento.yaml com marcador REVISAR."""
    proposta = tp.PropostaTipo(
        id_proposto="recibo_aluguel",
        n_amostras=4,
        exemplos_sha256=["abc"],
        exemplos_paths=["x.pdf"],
        regex_candidatos=["Recibo\\sde\\sAluguel"],
        mime_principal="application/pdf",
        extensao_principal=".pdf",
        confianca_global=0.85,
    )
    yaml = tmp_path / "tipos.yaml"
    yaml.write_text("tipos:\n  - id: existente\n", encoding="utf-8")
    info = tp._aceitar_proposta(proposta, yaml)
    assert info["id_proposto"] == "recibo_aluguel"
    conteudo = yaml.read_text(encoding="utf-8")
    assert "existente" in conteudo  # preserva entries antigos
    assert "recibo_aluguel" in conteudo
    assert "[REVISAR]" in conteudo
    assert "AUTO-TIPO-PROPOSTAS-DASHBOARD" in conteudo


# "Cada arquivo em _classificar/ é uma pergunta nao respondida." -- principio
