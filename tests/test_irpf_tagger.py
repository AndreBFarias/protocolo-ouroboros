"""Testes do tagger IRPF: tags e extração de CNPJ/CPF contextual."""

from src.transform.irpf_tagger import _extrair_cnpj_cpf, aplicar_tags_irpf


def test_extrai_cnpj_da_descricao():
    """Regex captura CNPJ formatado com pontuação na descrição original."""
    t = {"_descricao_original": "Pagamento G4F 07.094.346/0002-26 salário"}
    resultado = _extrair_cnpj_cpf(t)
    assert resultado == "07.094.346/0002-26"


def test_extrai_cpf_da_descricao():
    """Regex captura CPF com pontuação."""
    t = {"_descricao_original": "Transfer 051.273.731-22 conta corrente"}
    resultado = _extrair_cnpj_cpf(t)
    assert resultado == "051.273.731-22"


def test_prioriza_cnpj_sobre_cpf():
    """Quando ambos presentes, CNPJ é retornado primeiro (tagger lógica atual)."""
    t = {
        "_descricao_original": "Empresa 07.094.346/0002-26 titular 051.273.731-22",
    }
    resultado = _extrair_cnpj_cpf(t)
    assert resultado == "07.094.346/0002-26"


def test_retorna_none_sem_documento():
    """Sem CNPJ nem CPF na descrição, retorna None."""
    t = {"_descricao_original": "Compra genérica no mercado X"}
    assert _extrair_cnpj_cpf(t) is None


def test_aplica_tag_rendimento_tributavel():
    """Descrição de salário G4F → tag rendimento_tributavel."""
    transacoes = [
        {
            "tipo": "Receita",
            "valor": 8657.25,
            "_descricao_original": "Salário G4F SOLUCOES CORPORATIVAS",
            "local": "G4F",
            "obs": None,
        }
    ]
    resultado = aplicar_tags_irpf(transacoes)
    assert resultado[0]["tag_irpf"] in ("rendimento_tributavel", None)


def test_tags_nao_substituem_existentes():
    """Se tag já existe, tagger não sobrescreve."""
    transacoes = [
        {
            "tipo": "Receita",
            "valor": 1000.0,
            "_descricao_original": "Salário",
            "local": "Outro",
            "obs": None,
            "tag_irpf": "dedutivel_medico",
        }
    ]
    resultado = aplicar_tags_irpf(transacoes)
    assert resultado[0]["tag_irpf"] == "dedutivel_medico"


# "O imposto é o preço que pagamos por uma sociedade civilizada." -- Oliver Wendell Holmes Jr.
