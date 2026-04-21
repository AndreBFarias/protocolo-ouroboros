"""Testes de rótulos humanos no grafo visual -- Sprint 60.

Valida `src.graph.queries.label_humano` com os 5 cenários canônicos
descritos na spec: alias presente, alias vazio + razao_social, alias
vazio + metadata vazio, CNPJ puro, string longa.
"""

from __future__ import annotations

from src.graph.queries import label_humano


def test_label_humano_prefere_alias_quando_presente() -> None:
    """Caso 1: aliases[0] vence razao_social e nome_canonico."""
    node = {
        "aliases": '["Americanas", "Lojas Americanas SA"]',
        "metadata": '{"razao_social": "AMERICANAS S.A. EM RECUPERACAO JUDICIAL"}',
        "nome_canonico": "00.776.574/0160-79",
    }
    assert label_humano(node) == "Americanas"


def test_label_humano_usa_razao_social_quando_aliases_vazio() -> None:
    """Caso 2: aliases vazio -> metadata.razao_social."""
    node = {
        "aliases": "[]",
        "metadata": '{"razao_social": "Mercado Livre Brasil"}',
        "nome_canonico": "03.007.331/0001-41",
    }
    assert label_humano(node) == "Mercado Livre Brasil"


def test_label_humano_cai_no_nome_canonico_curto() -> None:
    """Caso 3: aliases vazio + metadata sem razao_social -> nome_canonico."""
    node = {
        "aliases": "[]",
        "metadata": "{}",
        "nome_canonico": "FORNECEDOR_X",
    }
    assert label_humano(node) == "FORNECEDOR_X"


def test_label_humano_cnpj_puro_retorna_cnpj() -> None:
    """Caso 4: CNPJ puro (sem alias, sem razao_social) devolve o próprio CNPJ."""
    node = {
        "aliases": None,
        "metadata": None,
        "nome_canonico": "00.776.574/0160-79",
    }
    assert label_humano(node) == "00.776.574/0160-79"


def test_label_humano_trunca_string_longa_em_40_chars() -> None:
    """Caso 5: nome_canonico > 40 chars é truncado com reticências no fim."""
    nome = "AMERICANAS S A EM RECUPERACAO JUDICIAL FILIAL 0337 CNPJ 00.776"
    node = {
        "aliases": "[]",
        "metadata": "{}",
        "nome_canonico": nome,
    }
    resultado = label_humano(node)
    assert resultado == nome[:40] + "..."
    assert len(resultado) == 43


def test_label_humano_aceita_aliases_ja_deserializado() -> None:
    """Regressão defensiva: camada dashboard já passa lista Python, não JSON string."""
    node = {
        "aliases": ["Neoenergia"],
        "metadata": {},
        "nome_canonico": "CNPJ_NEOENERGIA",
    }
    assert label_humano(node) == "Neoenergia"


def test_label_humano_ignora_alias_vazio_string() -> None:
    """Alias string vazia não conta -- cai no próximo fallback."""
    node = {
        "aliases": '["", "   "]',
        "metadata": '{"razao_social": "Razao Social Valida"}',
        "nome_canonico": "ID_QUALQUER",
    }
    # primeiro alias é string vazia: pula para razao_social
    assert label_humano(node) == "Razao Social Valida"


def test_label_humano_tolerante_a_json_invalido() -> None:
    """JSON malformado em aliases/metadata não quebra, cai no nome_canonico."""
    node = {
        "aliases": "{string quebrada",
        "metadata": "json inválido",
        "nome_canonico": "FALLBACK_CANONICO",
    }
    assert label_humano(node) == "FALLBACK_CANONICO"


# "Um bom rótulo é meio reconhecimento." -- princípio de clareza
