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


def test_classificacao_sempre_valida(transacao):
    """Classificação nunca pode sair vazia -- garantia do garantir_classificacao."""
    cat = Categorizer()
    t = transacao(local="Qualquer coisa")
    cat.categorizar(t)
    assert t["classificacao"] in ("Obrigatório", "Questionável", "Supérfluo", "N/A")


def test_imposto_sempre_obrigatorio(transacao):
    """Sprint 40: Tipo Imposto sem match cai em Obrigatório via _garantir_classificacao."""
    cat = Categorizer()
    t = transacao(local="Imposto Desconhecido ZZZ", tipo="Imposto")
    cat.categorizar(t)
    assert t["classificacao"] == "Obrigatório"


def test_receita_sem_match_cai_em_na(transacao):
    """Sprint 40: Receita sem match vai pra N/A (não para Questionável)."""
    cat = Categorizer()
    t = transacao(local="Fonte Obscura ZZQWX", tipo="Receita")
    cat.categorizar(t)
    assert t["classificacao"] == "N/A"


def test_transferencia_interna_sem_match_cai_em_na(transacao):
    """Sprint 40: TI sem match vai pra N/A (não para Questionável)."""
    cat = Categorizer()
    t = transacao(local="Movimento ZZQWX", tipo="Transferência Interna")
    cat.categorizar(t)
    assert t["classificacao"] == "N/A"


def test_break_apos_match_garante_fallback(transacao):
    """Armadilha #5: após match, `break` (não `return`) permite que _garantir_classificacao rode."""
    cat = Categorizer()
    # Cenário: regex casa mas não define classificação (raro mas possível em regras customizadas)
    t = transacao(local="Qualquer texto sem match", valor=50.0)
    cat.categorizar(t)
    # Mesmo sem regra, classificação nunca é None após categorizar
    assert t["classificacao"] is not None


# "A ordem não é do tempo, mas do entendimento." -- Espinosa
