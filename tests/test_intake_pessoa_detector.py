"""Testes do src.intake.pessoa_detector (Sprint 41b).

Cobre:
- 3 camadas de detecção (CPF mapeado, path-pai, fallback casal)
- Glyph-tolerant via extrair_cpf (CPF com espaço inserido por fonte quebrada)
- Mapping ausente, mapping malformado, CPF inválido (não 11 dígitos)
- Integração com orchestrator: pessoa="_indefinida" dispara auto-detect
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.intake import pessoa_detector as pd

# ============================================================================
# Helpers
# ============================================================================


def _yaml_mapping(tmp_path: Path, conteudo: str) -> Path:
    arq = tmp_path / "cpfs.yaml"
    arq.write_text(conteudo, encoding="utf-8")
    return arq


@pytest.fixture(autouse=True)
def reset_cache():
    """Limpa cache de mapping entre testes."""
    pd._CACHE_CPFS = None
    yield
    pd._CACHE_CPFS = None


# ============================================================================
# Camada 1 -- CPF do preview mapeado
# ============================================================================


def test_cpf_mapeado_devolve_pessoa_correspondente(tmp_path, monkeypatch):
    arq_yaml = _yaml_mapping(
        tmp_path,
        'cpfs:\n  "05127373122": andre\n  "97737068100": vitoria\n',
    )
    monkeypatch.setattr(pd, "_PATH_MAPPING", arq_yaml)
    arq = tmp_path / "doc.pdf"
    arq.write_bytes(b"x")

    pessoa, fonte = pd.detectar_pessoa(arq, "Cliente CPF: 051.273.731-22 segurado")
    assert pessoa == "andre"
    assert "CPF" in fonte


def test_cpf_glyph_corrompido_ainda_casa(tmp_path, monkeypatch):
    """O CPF do pdf_notas.pdf real aparece como '051.273. 731-22' (espaço)."""
    arq_yaml = _yaml_mapping(tmp_path, 'cpfs:\n  "05127373122": andre\n')
    monkeypatch.setattr(pd, "_PATH_MAPPING", arq_yaml)
    arq = tmp_path / "doc.pdf"
    arq.write_bytes(b"x")
    pessoa, _ = pd.detectar_pessoa(arq, "CPF: 051.273. 731-22")
    assert pessoa == "andre"


def test_cpf_nao_mapeado_cai_para_camada_2(tmp_path, monkeypatch):
    arq_yaml = _yaml_mapping(tmp_path, 'cpfs:\n  "05127373122": andre\n')
    monkeypatch.setattr(pd, "_PATH_MAPPING", arq_yaml)
    pasta_vit = tmp_path / "vitoria"
    pasta_vit.mkdir()
    arq = pasta_vit / "doc.pdf"
    arq.write_bytes(b"x")
    pessoa, fonte = pd.detectar_pessoa(arq, "CPF: 999.999.999-99 estranho")
    assert pessoa == "vitoria"
    assert "path" in fonte


# ============================================================================
# Camada 2 -- pasta-pai
# ============================================================================


def test_pasta_pai_andre_devolve_andre(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "_PATH_MAPPING", tmp_path / "inexistente.yaml")
    pasta = tmp_path / "andre"
    pasta.mkdir()
    arq = pasta / "doc.pdf"
    arq.write_bytes(b"x")
    pessoa, fonte = pd.detectar_pessoa(arq, preview_texto=None)
    assert pessoa == "andre"
    assert "path" in fonte


def test_pasta_pai_vitoria_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "_PATH_MAPPING", tmp_path / "inexistente.yaml")
    pasta = tmp_path / "VITORIA"
    pasta.mkdir()
    arq = pasta / "doc.pdf"
    arq.write_bytes(b"x")
    pessoa, _ = pd.detectar_pessoa(arq, preview_texto=None)
    assert pessoa == "vitoria"


# ============================================================================
# Camada 3 -- fallback casal
# ============================================================================


def test_sem_cpf_e_sem_pasta_devolve_casal(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "_PATH_MAPPING", tmp_path / "inexistente.yaml")
    arq = tmp_path / "doc.pdf"
    arq.write_bytes(b"x")
    pessoa, fonte = pd.detectar_pessoa(arq, preview_texto=None)
    assert pessoa == "casal"
    assert "fallback" in fonte


def test_preview_vazio_e_pasta_neutra_devolve_casal(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "_PATH_MAPPING", tmp_path / "inexistente.yaml")
    pasta = tmp_path / "outras"
    pasta.mkdir()
    arq = pasta / "doc.pdf"
    arq.write_bytes(b"x")
    pessoa, _ = pd.detectar_pessoa(arq, preview_texto="")
    assert pessoa == "casal"


def test_cpf_extraivel_mas_nao_mapeado_e_pasta_neutra_devolve_casal(tmp_path, monkeypatch):
    """Caso típico: arquivo da inbox/ flat com CPF de terceiro (loja, fornecedor)."""
    monkeypatch.setattr(pd, "_PATH_MAPPING", tmp_path / "inexistente.yaml")
    arq = tmp_path / "doc.pdf"
    arq.write_bytes(b"x")
    pessoa, _ = pd.detectar_pessoa(arq, preview_texto="CPF: 123.456.789-00 fornecedor X")
    assert pessoa == "casal"


# ============================================================================
# Carregamento do mapping
# ============================================================================


def test_mapping_ausente_carrega_vazio_sem_levantar(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "_PATH_MAPPING", tmp_path / "fantasma.yaml")
    mapeamento = pd.recarregar_mapeamento()
    assert mapeamento == {}


def test_mapping_aceita_cpf_com_pontuacao_normaliza_chave(tmp_path):
    arq = _yaml_mapping(
        tmp_path,
        'cpfs:\n  "051.273.731-22": andre\n  "977 370 681 00": vitoria\n',
    )
    mapeamento = pd.recarregar_mapeamento(arq)
    assert mapeamento["05127373122"] == "andre"
    assert mapeamento["97737068100"] == "vitoria"


def test_mapping_recusa_cpf_invalido_loga_warning(tmp_path):
    arq = _yaml_mapping(
        tmp_path,
        'cpfs:\n  "111": andre\n  "05127373122": andre\n',
    )
    mapeamento = pd.recarregar_mapeamento(arq)
    assert "111" not in mapeamento
    assert "05127373122" in mapeamento


def test_mapping_recusa_pessoa_invalida(tmp_path):
    arq = _yaml_mapping(tmp_path, 'cpfs:\n  "05127373122": rei_arthur\n')
    mapeamento = pd.recarregar_mapeamento(arq)
    assert "05127373122" not in mapeamento


def test_mapping_yaml_sem_chave_cpfs_devolve_vazio(tmp_path):
    """Se YAML tem outra estrutura, 'cpfs' default vira dict vazio -> mapeamento vazio."""
    arq = _yaml_mapping(tmp_path, "outras_coisas:\n  - 1\n")
    mapeamento = pd.recarregar_mapeamento(arq)
    assert mapeamento == {}


def test_mapping_yaml_nao_dict_levanta(tmp_path):
    arq = _yaml_mapping(tmp_path, "- linha 1\n- linha 2\n")
    with pytest.raises(ValueError, match="não é dict raiz"):
        pd.recarregar_mapeamento(arq)


# ============================================================================
# Integração com orchestrator
# ============================================================================


def test_orchestrator_pessoa_indefinida_dispara_autodetect(tmp_path, monkeypatch):
    """orchestrator com pessoa='_indefinida' chama detectar_pessoa."""
    from src.intake import classifier as clf
    from src.intake import extractors_envelope as env
    from src.intake import orchestrator as orq
    from src.intake import registry as reg
    from src.intake import router

    raiz = tmp_path / "repo"
    raiz.mkdir()
    monkeypatch.setattr(env, "_ENVELOPES_BASE", raiz / "data" / "raw" / "_envelopes")
    monkeypatch.setattr(router, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(
        router, "_ORIGINAIS_BASE", raiz / "data" / "raw" / "_envelopes" / "originais"
    )
    monkeypatch.setattr(clf, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(clf, "_PATH_DATA_RAW", raiz / "data" / "raw")
    monkeypatch.setattr(reg, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(reg, "_PATH_DATA_RAW", raiz / "data" / "raw")
    clf.recarregar_tipos()

    # mapping com o CPF 051.273.731-22 -> andre
    arq_yaml = raiz / "mappings_cpfs.yaml"
    arq_yaml.write_text('cpfs:\n  "05127373122": andre\n', encoding="utf-8")
    monkeypatch.setattr(pd, "_PATH_MAPPING", arq_yaml)

    # arquivo PDF nativo com CPF do André no preview
    from reportlab.pdfgen import canvas

    pseudo_inbox = raiz / "inbox"
    pseudo_inbox.mkdir(parents=True, exist_ok=True)
    arq = pseudo_inbox / "cupom.pdf"
    c = canvas.Canvas(str(arq))
    for i, linha in enumerate(
        [
            "CUPOM BILHETE DE SEGURO",
            "GARANTIA ESTENDIDA ORIGINAL",
            "Processo SUSEP 12345",
            "CPF: 051.273.731-22",
        ]
    ):
        c.drawString(50, 800 - i * 14, linha)
    c.showPage()
    c.save()

    relatorio = orq.processar_arquivo_inbox(arq, pessoa="_indefinida")
    assert len(relatorio.artefatos) == 1
    # Pasta destino tem que ser andre/, NÃO casal/ nem _indefinida/
    assert "/andre/" in str(relatorio.artefatos[0].caminho_final)


def test_orchestrator_pessoa_explicita_pula_autodetect(tmp_path, monkeypatch):
    """Quando pessoa é passada, não chama detectar_pessoa."""
    from src.intake import classifier as clf
    from src.intake import extractors_envelope as env
    from src.intake import orchestrator as orq
    from src.intake import registry as reg
    from src.intake import router

    raiz = tmp_path / "repo"
    raiz.mkdir()
    monkeypatch.setattr(env, "_ENVELOPES_BASE", raiz / "data" / "raw" / "_envelopes")
    monkeypatch.setattr(router, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(
        router, "_ORIGINAIS_BASE", raiz / "data" / "raw" / "_envelopes" / "originais"
    )
    monkeypatch.setattr(clf, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(clf, "_PATH_DATA_RAW", raiz / "data" / "raw")
    monkeypatch.setattr(reg, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(reg, "_PATH_DATA_RAW", raiz / "data" / "raw")
    clf.recarregar_tipos()

    # Sem mapping: se autodetect rodasse, cairia em "casal" pelo fallback
    monkeypatch.setattr(pd, "_PATH_MAPPING", raiz / "fantasma.yaml")

    pseudo_inbox = raiz / "inbox"
    pseudo_inbox.mkdir(parents=True, exist_ok=True)
    arq = pseudo_inbox / "doc.xml"
    arq.write_text('<?xml version="1.0"?><infNFe/>', encoding="utf-8")

    relatorio = orq.processar_arquivo_inbox(arq, pessoa="vitoria")
    # Pessoa explícita "vitoria" deve ser respeitada, não fallback "casal"
    assert "/vitoria/" in str(relatorio.artefatos[0].caminho_final)


# "Onde não há prova, não há acusação." -- princípio do direito civilizado
