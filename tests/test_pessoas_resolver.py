"""Testes do resolver canonico de pessoa (Sprint MOB-bridge-1).

Cobre os 6 cases declarados na spec MOB-bridge-1 secao 2:
    1. Resolução por CPF formatado e não formatado.
    2. Resolução por CNPJ raiz 8 digitos sem /0001-XX.
    3. Resolução por razao social case-insensitive.
    4. Resolução por alias.
    5. Fallback "casal" quando nada casa.
    6. pessoa_id_de_pasta cobrindo pessoa_a/pessoa_b/casal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.utils import pessoas as mod


@pytest.fixture
def yaml_sintetico(tmp_path: Path) -> Path:
    """Cria pessoas.yaml sintetico em tmp_path e aponta resolver pra ele."""
    arquivo = tmp_path / "pessoas.yaml"
    arquivo.write_text(
        """
pessoas:
  pessoa_a:
    display_name: "Titular A"
    cpfs:
      - "111.222.333-44"
    cnpjs:
      - "12.345.678/0001-90"
    razao_social:
      - "EMPRESA A LTDA"
    aliases:
      - "TITULAR A"
  pessoa_b:
    display_name: "Titular B"
    cpfs:
      - "555.666.777-88"
    cnpjs:
      - "99887766"
    razao_social:
      - "EMPRESA B SOCIEDADE INDIVIDUAL"
    aliases:
      - "TITULAR B"
fallback_pessoa: casal
""",
        encoding="utf-8",
    )
    mod.recarregar_pessoas(arquivo)
    yield arquivo
    # Restaura o yaml canonico do projeto apos cada teste.
    mod.recarregar_pessoas(mod._RAIZ_REPO / "mappings" / "pessoas.yaml")


def test_resolver_por_cpf_formatado(yaml_sintetico: Path) -> None:
    assert mod.resolver_pessoa(cpf="111.222.333-44") == "pessoa_a"


def test_resolver_por_cpf_nao_formatado(yaml_sintetico: Path) -> None:
    assert mod.resolver_pessoa(cpf="11122233344") == "pessoa_a"
    assert mod.resolver_pessoa(cpf="55566677788") == "pessoa_b"


def test_resolver_por_cnpj_raiz_8_digitos(yaml_sintetico: Path) -> None:
    # raiz com 8 digitos, sem /0001-XX -- ainda casa
    assert mod.resolver_pessoa(cnpj="12345678") == "pessoa_a"
    # raiz exatamente como declarada
    assert mod.resolver_pessoa(cnpj="99887766") == "pessoa_b"
    # CNPJ completo padrao também casa
    assert mod.resolver_pessoa(cnpj="12.345.678/0001-90") == "pessoa_a"


def test_resolver_por_razao_social_case_insensitive(yaml_sintetico: Path) -> None:
    assert mod.resolver_pessoa(razao_social="empresa a ltda") == "pessoa_a"
    assert mod.resolver_pessoa(razao_social="EMPRESA A LTDA") == "pessoa_a"
    assert mod.resolver_pessoa(razao_social="empresa b sociedade individual") == "pessoa_b"


def test_resolver_por_alias_case_insensitive(yaml_sintetico: Path) -> None:
    assert mod.resolver_pessoa(alias="titular a") == "pessoa_a"
    assert mod.resolver_pessoa(alias="Titular B") == "pessoa_b"


def test_fallback_quando_nada_casa(yaml_sintetico: Path) -> None:
    assert mod.resolver_pessoa(alias="desconhecido") == "casal"
    assert mod.resolver_pessoa(cpf="000.000.000-00") == "casal"
    assert mod.resolver_pessoa() == "casal"
    # fallback explicito do chamador respeitado quando válido
    assert mod.resolver_pessoa(fallback="pessoa_a") == "pessoa_a"
    # fallback inválido cai no default
    assert mod.resolver_pessoa(fallback="qualquer_outra_coisa") == "casal"


def test_pessoa_id_de_pasta_cobre_buckets_canonicos() -> None:
    # buckets genericos novos
    assert mod.pessoa_id_de_pasta("/tmp/data/raw/pessoa_a/itau/x.pdf") == "pessoa_a"
    assert mod.pessoa_id_de_pasta("/tmp/data/raw/pessoa_b/nubank/y.csv") == "pessoa_b"
    assert mod.pessoa_id_de_pasta("/tmp/data/raw/casal/boletos/z.pdf") == "casal"
    # buckets historicos (compatibilidade) são mapeados
    assert mod.pessoa_id_de_pasta("/tmp/data/raw/andre/c6/extrato.xls") == "pessoa_a"
    assert mod.pessoa_id_de_pasta("/tmp/data/raw/vitoria/nubank_pf_cc/x.csv") == "pessoa_b"
    # nada bate -> None
    assert mod.pessoa_id_de_pasta("/tmp/sem/bucket/conhecido.pdf") is None
    assert mod.pessoa_id_de_pasta("") is None


def test_nome_de_resolve_display_name(yaml_sintetico: Path) -> None:
    assert mod.nome_de("pessoa_a") == "Titular A"
    assert mod.nome_de("pessoa_b") == "Titular B"
    assert mod.nome_de("casal") == "Casal"
    # Id desconhecido cai no fallback "Casal" via pessoa_id_de_legacy.
    assert mod.nome_de("inexistente") == "Casal"
    # String vazia também cai em "Casal".
    assert mod.nome_de("") == "Casal"


def test_carregar_pessoas_estrutura_basica(yaml_sintetico: Path) -> None:
    dados = mod.carregar_pessoas()
    assert "pessoas" in dados
    assert "pessoa_a" in dados["pessoas"]
    assert "pessoa_b" in dados["pessoas"]
    assert dados["pessoas"]["pessoa_a"]["display_name"] == "Titular A"


# "Onde não ha lei, não ha liberdade." -- John Locke
