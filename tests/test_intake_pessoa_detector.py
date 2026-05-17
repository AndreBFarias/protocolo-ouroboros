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

    # arquivo PDF nativo com CPF do André no preview  # anonimato-allow: comentario narrativo
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


# ============================================================================
# Sprint 90 -- identidade rica via pessoas.yaml (CNPJ + razão social + alias)
# ============================================================================


def _yaml_pessoas(tmp_path: Path, conteudo: str) -> Path:
    arq = tmp_path / "pessoas.yaml"
    arq.write_text(conteudo, encoding="utf-8")
    return arq


@pytest.fixture
def pessoas_yaml_casal(tmp_path, monkeypatch):
    """Fixture: yaml de pessoas.yaml configurado para o casal real."""
    arq = _yaml_pessoas(
        tmp_path,
        """
pessoas:
  andre:
    cpfs:
      - "051.273.731-22"
    cnpjs:
      - "45.850.636/0001-60"
    razao_social:
      - "ANDRE DA SILVA BATISTA DE FARIAS"
      - "ANDRE SILVA BATISTA FARIAS"
    aliases:
      - "ANDRE FARIAS"
  vitoria:
    cpfs:
      - "070.475.321-96"
    cnpjs:
      - "52.488.753"
    razao_social:
      - "VITORIA MARIA SILVA DOS SANTOS"
    aliases:
      - "VITORIA"
fallback_pessoa: casal
""",
    )
    monkeypatch.setattr(pd, "_PATH_PESSOAS", arq)
    monkeypatch.setattr(pd, "_PATH_MAPPING", tmp_path / "cpfs_inexistente.yaml")
    pd._CACHE_PESSOAS = None
    pd._CACHE_CPFS = None
    return arq


def test_detecta_andre_por_cnpj_mei_desativado(tmp_path, pessoas_yaml_casal):
    """DAS PARCSN tem CNPJ 45.850.636/0001-60 + razão social ANDRE..."""
    arq = tmp_path / "das.pdf"
    arq.write_bytes(b"x")
    texto = (
        "Documento de Arrecadação do Simples Nacional\n"
        "CNPJ Razão Social\n"
        "45.850.636/0001-60 ANDRE DA SILVA BATISTA DE FARIAS\n"
    )
    pessoa, fonte = pd.detectar_pessoa(arq, texto)
    assert pessoa == "andre"
    assert "CNPJ" in fonte or "razão social" in fonte


def test_detecta_andre_por_razao_social_sem_cpf(tmp_path, pessoas_yaml_casal):
    """Certidão Receita CNPJ sem CPF, só razão social."""
    arq = tmp_path / "cert.pdf"
    arq.write_bytes(b"x")
    texto = "Certidão emitida para: ANDRE DA SILVA BATISTA DE FARIAS"
    pessoa, fonte = pd.detectar_pessoa(arq, texto)
    assert pessoa == "andre"


def test_detecta_vitoria_por_razao_social(tmp_path, pessoas_yaml_casal):
    arq = tmp_path / "doc.pdf"
    arq.write_bytes(b"x")
    texto = "PIX recebido de VITORIA MARIA SILVA DOS SANTOS - 070.475..."
    pessoa, _ = pd.detectar_pessoa(arq, texto)
    assert pessoa == "vitoria"


def test_detecta_vitoria_por_cnpj_mei_ativo(tmp_path, pessoas_yaml_casal):
    arq = tmp_path / "doc.pdf"
    arq.write_bytes(b"x")
    texto = "Nota Fiscal emitida por CNPJ 52.488.753/0001-10"
    pessoa, fonte = pd.detectar_pessoa(arq, texto)
    assert pessoa == "vitoria"
    assert "CNPJ" in fonte


def test_cnpj_vence_razao_social_ambigua(tmp_path, pessoas_yaml_casal):
    """CNPJ é mais específico que razão social -- vence ordem."""
    arq = tmp_path / "doc.pdf"
    arq.write_bytes(b"x")
    texto = "CNPJ 45.850.636/0001-60 VITORIA MARIA SILVA DOS SANTOS"
    pessoa, fonte = pd.detectar_pessoa(arq, texto)
    # CNPJ do André vence razão social da Vitória no mesmo texto  # anonimato-allow
    assert pessoa == "andre"
    assert "CNPJ" in fonte


def test_fallback_casal_sem_identificador(tmp_path, pessoas_yaml_casal):
    arq = tmp_path / "doc.pdf"
    arq.write_bytes(b"x")
    pessoa, fonte = pd.detectar_pessoa(arq, "documento genérico sem dados")
    assert pessoa == "casal"
    assert "fallback" in fonte


def test_cpf_literal_ainda_vence_cnpj(tmp_path, monkeypatch):
    """Retrocompat: CPF mapeado em cpfs_pessoas.yaml vence mesmo se pessoas.yaml não existe."""
    cpfs_yaml = _yaml_mapping(tmp_path, 'cpfs:\n  "05127373122": andre\n')
    monkeypatch.setattr(pd, "_PATH_MAPPING", cpfs_yaml)
    monkeypatch.setattr(pd, "_PATH_PESSOAS", tmp_path / "pessoas_inexistente.yaml")
    pd._CACHE_CPFS = None
    pd._CACHE_PESSOAS = None

    arq = tmp_path / "doc.pdf"
    arq.write_bytes(b"x")
    pessoa, fonte = pd.detectar_pessoa(arq, "CPF: 051.273.731-22 tudo mais")
    assert pessoa == "andre"
    assert "CPF" in fonte


# ============================================================================
# Sprint INTAKE-FALLBACK-CPFS-AUSENTE (2026-05-17)
# Quando cpfs_pessoas.yaml ausente mas .example existe (clone novo
# típico), detector deve logar WARNING explicito.
# ============================================================================


def test_yaml_ausente_com_example_loga_warning(tmp_path, monkeypatch, caplog):
    """Clone novo: .yaml ausente + .example presente → WARNING explicito."""
    import logging

    yaml_inexistente = tmp_path / "cpfs_pessoas.yaml"
    yaml_example = tmp_path / "cpfs_pessoas.yaml.example"
    yaml_example.write_text('cpfs:\n  "00000000000": pessoa_a\n', encoding="utf-8")

    monkeypatch.setattr(pd, "_PATH_MAPPING", yaml_inexistente)
    pd._CACHE_CPFS = None
    with caplog.at_level(logging.WARNING, logger="pessoa_detector"):
        resultado = pd.recarregar_mapeamento()
    assert resultado == {}
    assert any("cpfs_pessoas.yaml AUSENTE" in r.message for r in caplog.records)


def test_yaml_ausente_sem_example_apenas_debug(tmp_path, monkeypatch, caplog):
    """Estado anômalo: nem .yaml nem .example. Loga DEBUG (não warning)."""
    import logging

    yaml_inexistente = tmp_path / "cpfs_pessoas.yaml"
    monkeypatch.setattr(pd, "_PATH_MAPPING", yaml_inexistente)
    pd._CACHE_CPFS = None
    with caplog.at_level(logging.WARNING, logger="pessoa_detector"):
        resultado = pd.recarregar_mapeamento()
    assert resultado == {}
    # Nenhum WARNING (porque nem .example existe — estado totalmente novo):
    msgs_warning = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert not any("AUSENTE" in m for m in msgs_warning)


# "Onde não há prova, não há acusação." -- princípio do direito civilizado
