"""Testes do override estrutural Salario G4F C6 (Sprint INFRA-CATEGORIZAR-SALARIO-G4F-C6).

Cenario coberto:
    Salario liquido G4F do Andre (R$ 6.381,14) chega ao C6 como transferencia interna
    apos passar pelo Santander declarado no holerite. A descricao bruta nao contem  # noqa: accent
    "G4F" entao o regex de categorias.yaml nao casa. O override estrutural em  # noqa: accent
    mappings/overrides.yaml "__SALARIO_G4F_C6__" reconhece o padrao pela combinacao
    banco_origem=C6 + 6000 <= valor <= 7000 + dia do mes entre 1 e 10.
"""

from datetime import date

from src.transform.categorizer import Categorizer


def test_aplica_quando_valor_banco_e_data_batem(transacao):
    """Caso real auditoria: R$ 6.381,14 em 06/03/2026 banco C6 -> Salario + IRPF."""
    cat = Categorizer()
    t = transacao(
        local="Transferencia recebida",
        banco="C6",
        valor=6381.14,
        tipo="Transferência Interna",
        data_t=date(2026, 3, 6),
        descricao_original="Transferencia recebida",
    )
    cat.categorizar(t)
    assert t["categoria"] == "Salário"
    assert t["tipo"] == "Receita"
    assert t["tag_irpf"] == "rendimento_tributavel"


def test_nao_aplica_se_banco_diferente(transacao):
    """Mesmo valor e data no Itaú não deve virar Salário G4F (regra é exclusiva do C6)."""
    cat = Categorizer()
    t = transacao(
        local="Credito generico",
        banco="Itaú",
        valor=6381.14,
        tipo="Transferência Interna",
        data_t=date(2026, 3, 6),
        descricao_original="Credito generico",
    )
    cat.categorizar(t)
    assert t["categoria"] != "Salário"
    assert t.get("tag_irpf") != "rendimento_tributavel"


def test_nao_aplica_se_valor_fora_da_faixa(transacao):
    """Valor abaixo da faixa (R$ 500) no C6 não deve virar Salário."""
    cat = Categorizer()
    t = transacao(
        local="Transferencia recebida",
        banco="C6",
        valor=500.0,
        tipo="Transferência Interna",
        data_t=date(2026, 3, 6),
        descricao_original="Transferencia recebida",
    )
    cat.categorizar(t)
    assert t["categoria"] != "Salário"


def test_nao_aplica_se_data_fora_da_janela(transacao):
    """Mesmo valor no C6 mas no dia 25 não deve virar Salário (fora da janela 1-10)."""
    cat = Categorizer()
    t = transacao(
        local="Transferencia recebida",
        banco="C6",
        valor=6381.14,
        tipo="Transferência Interna",
        data_t=date(2026, 3, 25),
        descricao_original="Transferencia recebida",
    )
    cat.categorizar(t)
    assert t["categoria"] != "Salário"


def test_tag_irpf_aplicada_apos_match(transacao):
    """Apos aplicar override, tag IRPF deve estar setada (entra no pacote IRPF)."""
    cat = Categorizer()
    t = transacao(
        local="Transferencia",
        banco="C6",
        valor=6500.0,
        tipo="Transferência Interna",
        data_t=date(2026, 4, 7),
        descricao_original="Transferencia",
    )
    cat.categorizar(t)
    assert t["tag_irpf"] == "rendimento_tributavel"


def test_aplica_no_limite_inferior_da_janela(transacao):
    """Dia 1 do mes (limite inferior inclusivo) deve aplicar a regra."""
    cat = Categorizer()
    t = transacao(
        local="Transferencia",
        banco="C6",
        valor=6381.14,
        tipo="Transferência Interna",
        data_t=date(2026, 5, 1),
        descricao_original="Transferencia",
    )
    cat.categorizar(t)
    assert t["categoria"] == "Salário"


# "Salario nao chamado de salario nao entra no IRPF -- e o tipo de drift  # noqa: accent
# que custa multa em marco do ano seguinte." -- principio da sprint
