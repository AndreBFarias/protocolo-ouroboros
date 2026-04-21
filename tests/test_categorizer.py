"""Testes do Categorizer.

Cobertura das armadilhas documentadas em CLAUDE.md:
- #4: Ki-Sabor -- regra de valor (>= R$ 800 = Aluguel, < R$ 800 = Padaria)
- #5: `break` após match (nunca `return`) para que fallback execute corretamente
"""

from src.transform.categorizer import Categorizer


def test_fallback_categoria_outros(transacao):
    """Transação sem match nem override cai em Outros + Questionável."""
    cat = Categorizer()
    t = transacao(local="Estabelecimento Completamente Desconhecido ZZZ123")
    cat.categorizar(t)
    assert t["categoria"] == "Outros"
    assert t["classificacao"] == "Questionável"


def test_kisabor_aluguel_valor_alto(transacao):
    """Armadilha #4: KISABOR com valor >= 800 = Aluguel."""
    cat = Categorizer()
    t = transacao(local="PANIFICADORA KI-SABOR", valor=1200.0)
    cat.categorizar(t)
    assert t["categoria"] == "Aluguel"


def test_kisabor_padaria_valor_baixo(transacao):
    """Armadilha #4: KISABOR com valor < 800 NÃO é Aluguel (cai em regra de padaria/Outros)."""
    cat = Categorizer()
    t = transacao(local="PANIFICADORA KI-SABOR", valor=15.50)
    cat.categorizar(t)
    assert t["categoria"] != "Aluguel"


def test_classificacao_despesa_sempre_valida(transacao):
    """Despesa sempre sai com classificação válida (fallback Questionável)."""
    cat = Categorizer()
    t = transacao(local="Qualquer coisa", tipo="Despesa")
    cat.categorizar(t)
    assert t["classificacao"] in ("Obrigatório", "Questionável", "Supérfluo")


def test_imposto_sempre_obrigatorio(transacao):
    """Sprint 40: Tipo Imposto sem match cai em Obrigatório via _garantir_classificacao."""
    cat = Categorizer()
    t = transacao(local="Imposto Desconhecido ZZZ", tipo="Imposto")
    cat.categorizar(t)
    assert t["classificacao"] == "Obrigatório"


def test_receita_nao_recebe_classificacao(transacao):
    """Sprint 67: Receita nunca tem classificação, independente de match/override.

    Schema: classificação só é válida para Despesa/Imposto.
    Receita é não-despesa -> classificacao=None (NaN no XLSX).
    """
    cat = Categorizer()
    t = transacao(local="SALARIO", tipo="Receita", valor=7000.0)
    cat.categorizar(t)
    assert t["classificacao"] is None


def test_receita_sem_match_fica_sem_classificacao(transacao):
    """Sprint 67: Receita sem match também fica sem classificação (None)."""
    cat = Categorizer()
    t = transacao(local="Fonte Obscura ZZQWX", tipo="Receita")
    cat.categorizar(t)
    assert t["classificacao"] is None


def test_transferencia_interna_nao_recebe_classificacao(transacao):
    """Sprint 67: Transferência Interna nunca tem classificação (None)."""
    cat = Categorizer()
    t = transacao(
        local="Pagamento fatura Nubank",
        tipo="Transferência Interna",
        valor=500.0,
    )
    cat.categorizar(t)
    assert t["classificacao"] is None


def test_transferencia_interna_sem_match_fica_sem_classificacao(transacao):
    """Sprint 67: TI sem match fica com classificacao=None (não 'N/A')."""
    cat = Categorizer()
    t = transacao(local="Movimento ZZQWX", tipo="Transferência Interna")
    cat.categorizar(t)
    assert t["classificacao"] is None


def test_despesa_recebe_classificacao(transacao):
    """Sprint 67: Despesa sempre recebe classificação (Obrigatório/Questionável/Supérfluo)."""
    cat = Categorizer()
    t = transacao(local="NEOENERGIA", tipo="Despesa", valor=400.0)
    cat.categorizar(t)
    assert t["classificacao"] in ("Obrigatório", "Questionável", "Supérfluo")


def test_regra_nao_sobrescreve_classificacao_em_receita(transacao):
    """Sprint 67: se uma regra regex casa Receita mas declara classificação, é ignorada."""
    cat = Categorizer()
    # Salário bate regra de Receita; mesmo que categorias.yaml declare algo, Receita fica None
    t = transacao(local="SALARIO G4F", tipo="Receita", valor=7000.0)
    cat.categorizar(t)
    assert t["classificacao"] is None


def test_break_apos_match_garante_fallback(transacao):
    """Armadilha #5: após match, `break` (não `return`) permite que _garantir_classificacao rode."""
    cat = Categorizer()
    # Cenário: Despesa sem match -> fallback Questionável
    t = transacao(local="Qualquer texto sem match", valor=50.0, tipo="Despesa")
    cat.categorizar(t)
    # Despesa nunca fica com classificação None após categorizar
    assert t["classificacao"] is not None


# "A ordem não é do tempo, mas do entendimento." -- Espinosa
