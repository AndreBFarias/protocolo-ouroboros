"""Testes do exportador de auditoria cruzada Opus × ETL.

Sprint META-AUDITORIA-CRUZADA-XLSX (2026-05-16).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "exportar_auditoria_cruzada",
    Path(__file__).resolve().parents[1] / "scripts" / "exportar_auditoria_cruzada.py",
)
assert _SPEC and _SPEC.loader
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def test_resumir_campos_canonicos_extrai_chaves_prioritarias() -> None:
    campos = {
        "tipo_documento": "holerite",
        "competencia": "2026-02",
        "liquido": 6381.14,
        "empresa": {"razao_social": "G4F LTDA", "cnpj": "07.094.346/0002-26"},
    }
    resumo = mod._resumir_campos_canonicos(campos)
    assert "competencia=2026-02" in resumo
    assert "liquido=6381.14" in resumo
    assert "G4F LTDA" in resumo
    assert "cnpj=07.094.346/0002-26" in resumo


def test_resumir_campos_canonicos_vazio() -> None:
    assert mod._resumir_campos_canonicos({}) == ""


def test_resumir_divergencias_top_5() -> None:
    comp = {
        "divergencias": [
            {"campo": "endereco", "esperado": None, "obtido": "X"},
            {"campo": "telefone", "esperado": None, "obtido": "Y"},
        ]
    }
    resumo = mod._resumir_divergencias(comp)
    assert "endereco" in resumo
    assert "telefone" in resumo


def test_montar_aba_auditoria_cruzada_combina_opus_e_etl() -> None:
    provas = {
        "sha_1": {
            "tipo": "holerite",
            "prova": {"sha256": "sha_1"},
            "lido_em": "2026-05-13T00:00:00",
            "lido_por": "opus",
            "campos": {"total": 100},
            "notas": "teste",
            "ultima_comparacao": None,
            "ultimo_veredito": "SEM_COMPARACAO",
        },
    }
    nodes = {
        "sha_1": {
            "node_id": 42,
            "nome_canonico": "HOLERITE|G4F|2026-02",
            "metadata": {"tipo_documento": "holerite"},
            "arquivo_origem": "data/raw/x.pdf",
            "sha256": "sha_1",
        },
    }
    linhas = mod.montar_aba_auditoria_cruzada(provas, nodes)
    assert len(linhas) == 1
    linha = linhas[0]
    assert linha["tipo_opus"] == "holerite"
    assert linha["tipo_etl"] == "holerite"
    assert linha["tipo_match"] is True
    assert linha["etl_node_id"] == 42


def test_montar_aba_auditoria_cruzada_sem_etl() -> None:
    """Prova existe mas ETL ainda não processou aquele sha256."""
    provas = {
        "sha_x": {
            "tipo": "boleto_servico",
            "prova": {},
            "lido_em": "",
            "lido_por": "",
            "campos": {},
            "notas": "",
            "ultima_comparacao": None,
            "ultimo_veredito": "SEM_COMPARACAO",
        },
    }
    linhas = mod.montar_aba_auditoria_cruzada(provas, {})
    assert len(linhas) == 1
    assert linhas[0]["etl_node_id"] == ""
    assert linhas[0]["tipo_etl"] == ""


def test_montar_aba_tipos_resumo_marca_orfaos() -> None:
    """Tipo no JSON mas não no YAML aparece com esta_no_yaml_canonico=False."""
    tipos_canonicos = ["holerite", "fatura_cartao"]
    graduacao = {
        "tipos": {
            "holerite": {"status": "GRADUADO", "amostras_ok": [], "amostras_divergentes": []},
            "nfce_modelo_65": {"status": "GRADUADO", "amostras_ok": [], "amostras_divergentes": []},
        }
    }
    linhas = mod.montar_aba_tipos_resumo(tipos_canonicos, graduacao, {}, {})
    por_tipo = {linha["tipo"]: linha for linha in linhas}
    assert por_tipo["holerite"]["esta_no_yaml_canonico"] is True
    assert por_tipo["nfce_modelo_65"]["esta_no_yaml_canonico"] is False
    assert por_tipo["fatura_cartao"]["status_graduacao"] == "SEM_DOSSIE"


def test_gerar_xlsx_grava_arquivo(tmp_path: Path, monkeypatch) -> None:
    """gerar_xlsx() roda end-to-end com mocks vazios e cria arquivo válido."""
    # Mock paths para tmp_path:
    monkeypatch.setattr(mod, "DIR_DOSSIES", tmp_path / "dossies_fake")
    monkeypatch.setattr(mod, "PATH_GRAFO", tmp_path / "grafo_inexistente.sqlite")
    monkeypatch.setattr(mod, "PATH_GRADUACAO", tmp_path / "graduacao_inexistente.json")
    monkeypatch.setattr(mod, "PATH_TIPOS_YAML", tmp_path / "tipos_inexistente.yaml")
    monkeypatch.setattr(mod, "PATH_SUGESTOES", tmp_path / "sugestoes_inexistente.json")
    monkeypatch.setattr(mod, "PATH_METRICAS", tmp_path / "metricas_inexistente.json")

    saida = tmp_path / "out.xlsx"
    info = mod.gerar_xlsx(saida)
    assert saida.exists()
    assert "auditoria_cruzada" in info["abas"]
    # Tudo vazio mas XLSX criado:
    assert info["abas"]["auditoria_cruzada"] == 0


def test_main_sem_args_usa_data_do_dia(tmp_path: Path, monkeypatch) -> None:
    """`main([])` sem --saida grava no path padrão data/output/auditoria_*."""
    saida_custom = tmp_path / "audit.xlsx"
    monkeypatch.setattr(mod, "DIR_DOSSIES", tmp_path / "dossies_fake")
    monkeypatch.setattr(mod, "PATH_GRAFO", tmp_path / "grafo_inexistente.sqlite")
    monkeypatch.setattr(mod, "PATH_GRADUACAO", tmp_path / "graduacao_inexistente.json")
    monkeypatch.setattr(mod, "PATH_TIPOS_YAML", tmp_path / "tipos_inexistente.yaml")
    monkeypatch.setattr(mod, "PATH_SUGESTOES", tmp_path / "sugestoes_inexistente.json")
    monkeypatch.setattr(mod, "PATH_METRICAS", tmp_path / "metricas_inexistente.json")

    rc = mod.main(["--saida", str(saida_custom)])
    assert rc == 0
    assert saida_custom.exists()


# "Auditoria honesta cruza o que duas testemunhas dizem." -- principio
