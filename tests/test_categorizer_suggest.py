"""Testes do sugestor TF-IDF.

Sprint CATEGORIZER-SUGESTAO-TFIDF (2026-05-16). Cobre helpers
puros + integração `gerar_sugestoes`.
"""

from __future__ import annotations

from src.transform.categorizer_suggest import (
    Transacao,
    _cosseno,
    _idf,
    _tfidf,
    _tokenizar,
    gerar_sugestoes,
)


def test_tokenizar_extrai_palavras_e_numeros() -> None:
    tokens = _tokenizar("Pagamento Uber - viagem 123")
    assert "pagamento" in tokens
    assert "uber" in tokens
    assert "viagem" in tokens
    assert "123" in tokens


def test_idf_inversamente_proporcional_a_frequencia() -> None:
    """Token em todos os docs → IDF baixo. Token raro → IDF alto."""
    textos = [["uber", "viagem"], ["uber", "comida"], ["mercado", "compra"]]
    idf = _idf(textos)
    # "uber" aparece em 2/3 docs
    # "mercado" aparece em 1/3 — IDF mais alto
    assert idf["mercado"] > idf["uber"]


def test_cosseno_vetores_identicos_eh_um() -> None:
    """Cosseno de vetor consigo mesmo é 1.0 (tolerância float)."""
    a = {"x": 1.0, "y": 2.0}
    assert _cosseno(a, a) == 1.0 or abs(_cosseno(a, a) - 1.0) < 1e-9


def test_cosseno_vetores_disjuntos_eh_zero() -> None:
    assert _cosseno({"x": 1.0}, {"y": 1.0}) == 0.0


def test_tfidf_zera_token_sem_idf() -> None:
    vec = _tfidf(["raro"], {"raro": 0.0})
    assert vec == {}


def test_gerar_sugestoes_dataset_minimo() -> None:
    """Treino com 3 categorias. Alvo 'Outros' deve casar com vizinho."""
    transacoes = [
        Transacao(id="1", descricao="Uber para casa", categoria="TRANSPORTE"),
        Transacao(id="2", descricao="Uber centro", categoria="TRANSPORTE"),
        Transacao(id="3", descricao="Padaria do bairro", categoria="ALIMENTACAO"),
        Transacao(id="4", descricao="Restaurante chines", categoria="ALIMENTACAO"),
        Transacao(id="5", descricao="Uber viagem aeroporto", categoria="Outros"),
        Transacao(id="6", descricao="Padaria express", categoria="Outros"),
    ]
    sug = gerar_sugestoes(transacoes)
    assert "5" in sug
    assert sug["5"]["top1"] == "TRANSPORTE"
    assert "6" in sug
    assert sug["6"]["top1"] == "ALIMENTACAO"


def test_gerar_sugestoes_sem_outros_devolve_vazio() -> None:
    transacoes = [
        Transacao(id="1", descricao="Uber", categoria="TRANSPORTE"),
        Transacao(id="2", descricao="Padaria", categoria="ALIMENTACAO"),
    ]
    assert gerar_sugestoes(transacoes) == {}


def test_gerar_sugestoes_sem_treino_devolve_vazio() -> None:
    """Se todas são Outros, não há treino para predição."""
    transacoes = [
        Transacao(id="1", descricao="x", categoria="Outros"),
        Transacao(id="2", descricao="y", categoria="Outros"),
    ]
    assert gerar_sugestoes(transacoes) == {}


def test_gerar_sugestoes_descricao_disjunta_sem_vizinhos() -> None:
    """Outros com tokens 100% novos não recebe sugestão."""
    transacoes = [
        Transacao(id="1", descricao="alpha beta", categoria="X"),
        Transacao(id="2", descricao="gamma delta", categoria="Outros"),
    ]
    sug = gerar_sugestoes(transacoes)
    # 2 não casa nada do treino — devolve vazio:
    assert "2" not in sug


# "Outros é débito cognitivo acumulado." -- principio
