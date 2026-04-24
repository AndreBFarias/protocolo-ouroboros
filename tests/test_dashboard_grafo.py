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


# ---------------------------------------------------------------------------
# Sprint 92a item 1 -- labels humanos em nodes transacao  # noqa: accent
# ---------------------------------------------------------------------------


def test_label_humano_transacao_usa_data_valor_local() -> None:
    """Transação sem alias mostra `<data> R$ <valor> <local>` em vez de hash."""
    node = {
        "tipo": "transacao",
        "aliases": "[]",
        "metadata": {
            "data": "2026-03-17",
            "valor": 103.93,
            "local": "SESC CONSULTORIOS",
        },
        "nome_canonico": "5c277bc27e632aa11fe4f0c9d28e1a7d0bb47b0f2a1d4a9b8c3e2f1a4b5c6d7e",
    }
    rotulo = label_humano(node)
    assert "2026-03-17" in rotulo
    assert "R$ 103,93" in rotulo
    assert "SESC" in rotulo


def test_label_humano_transacao_formata_valor_ptbr() -> None:
    """Valor em formato PT-BR (vírgula decimal, ponto de milhar)."""
    node = {
        "tipo": "transacao",
        "metadata": {
            "data": "2026-04-01",
            "valor": 1234.56,
            "local": "Mercadão",
        },
        "nome_canonico": "aaaaaaaa" * 8,
    }
    assert label_humano(node) == "2026-04-01 R$ 1.234,56 Mercadão"


def test_label_humano_transacao_aceita_valor_negativo() -> None:
    """Valor negativo é exibido pelo valor absoluto (nunca sinal no label)."""
    node = {
        "tipo": "transacao",
        "metadata": {"data": "2026-03-17", "valor": -103.93, "local": "SESC"},
        "nome_canonico": "hash",
    }
    rotulo = label_humano(node)
    assert "R$ 103,93" in rotulo
    assert "-" not in rotulo.split(" ")[2]  # valor não carrega sinal


def test_label_humano_transacao_trunca_local_longo_em_20() -> None:
    """Local muito longo é truncado em 17 chars + reticências."""
    node = {
        "tipo": "transacao",
        "metadata": {
            "data": "2026-03-17",
            "valor": 50.0,
            "local": "LOJA MUITO COMPRIDA DE FATO MUITO GRANDE",
        },
        "nome_canonico": "hash",
    }
    rotulo = label_humano(node)
    assert rotulo.endswith("...")
    # formato: "2026-03-17 R$ 50,00 LOJA MUITO COMPR..."
    parte_local = rotulo.split(" R$ ")[1].split(" ", 1)[1]
    assert len(parte_local) == 20  # 17 chars + "..."


def test_label_humano_transacao_sem_local_ainda_funciona() -> None:
    """Transação sem local ainda retorna data + valor (sem sufixo)."""
    node = {
        "tipo": "transacao",
        "metadata": {"data": "2026-03-17", "valor": 50.0},
        "nome_canonico": "hash",
    }
    assert label_humano(node) == "2026-03-17 R$ 50,00"


def test_label_humano_transacao_sem_data_cai_para_fallback() -> None:
    """Metadata incompleta volta ao comportamento padrão (razao_social/nc)."""
    node = {
        "tipo": "transacao",
        "aliases": "[]",
        "metadata": {"valor": 50.0, "local": "FOO"},  # sem data
        "nome_canonico": "FORNECEDOR_SEM_HASH",
    }
    # Sem data: cai no fallback razao_social (ausente) -> nome_canonico.
    assert label_humano(node) == "FORNECEDOR_SEM_HASH"


def test_label_humano_transacao_prioridade_alias_sobre_metadata() -> None:
    """Se transação tem alias humano, alias vence (back-compat Sprint 60)."""
    node = {
        "tipo": "transacao",
        "aliases": '["PIX Vitória"]',
        "metadata": {"data": "2026-03-17", "valor": 50.0, "local": "Local"},
        "nome_canonico": "hash",
    }
    assert label_humano(node) == "PIX Vitória"


def test_rotulo_humano_tipo_retorna_acentuado() -> None:
    """Helper de rótulo expõe acentuação PT-BR sem mexer na chave canônica."""
    from src.dashboard.componentes.grafo_pyvis import (
        COR_POR_TIPO,
        rotulo_humano_tipo,
    )

    # Chaves do dict seguem o schema N-para-N (sem acento).
    assert "transacao" in COR_POR_TIPO
    assert "periodo" in COR_POR_TIPO
    assert "transação" not in COR_POR_TIPO  # nunca vira chave
    assert "período" not in COR_POR_TIPO

    # Mas o rótulo exibido ao humano é acentuado.
    assert rotulo_humano_tipo("transacao") == "transação"
    assert rotulo_humano_tipo("periodo") == "período"
    assert rotulo_humano_tipo("prescricao") == "prescrição"
    assert rotulo_humano_tipo("apolice") == "apólice"
    assert rotulo_humano_tipo("tipo_desconhecido") == "tipo_desconhecido"


def test_grafo_pyvis_usa_label_canonico_para_transacao() -> None:
    """_label_humano do pyvis delega ao canônico e mantém truncagem 30 no pyvis."""
    from src.dashboard.componentes import grafo_pyvis

    node = {
        "id": 42,
        "tipo": "transacao",
        "aliases": "[]",
        "metadata": {
            "data": "2026-03-17",
            "valor": 103.93,
            "local": "SESC CONSULTORIOS",
        },
        "nome_canonico": "abcdef0123456789" * 4,  # hash-like 64 hex
    }
    resultado = grafo_pyvis._label_humano(node)
    # Deve ter montado via metadata, não caído no fallback "transacao#42".
    assert "2026-03-17" in resultado
    assert "R$" in resultado
    # Mantém limite de 40 chars (`nc[:37] + "..."`).
    assert len(resultado) <= 40


def test_grafo_pyvis_fallback_hash_like_quando_metadata_vazia() -> None:
    """Sem metadata utilizável, nó com nc hash cai em `<tipo>#<id>`."""
    from src.dashboard.componentes import grafo_pyvis

    node = {
        "id": 99,
        "tipo": "transacao",
        "aliases": "[]",
        "metadata": "{}",
        "nome_canonico": "abcdef0123456789" * 4,  # 64 hex chars
    }
    assert grafo_pyvis._label_humano(node) == "transacao#99"


# "Um bom rótulo é meio reconhecimento." -- princípio de clareza
