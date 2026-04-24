"""Sprint 92a.10: testes do cartão colorido de ritmo em Projeções."""

from __future__ import annotations

from src.dashboard.paginas.projecoes import (
    _cor_por_sinal_ritmo,
    _metric_ritmo_html,
)
from src.dashboard.tema import CORES


def test_cor_por_sinal_positivo_retorna_verde_dracula() -> None:
    """Valor positivo usa cor Dracula positivo (#50FA7B)."""
    assert _cor_por_sinal_ritmo(1234.56) == CORES["positivo"]


def test_cor_por_sinal_negativo_retorna_vermelho_dracula() -> None:
    """Valor negativo usa cor Dracula negativo (#FF5555)."""
    assert _cor_por_sinal_ritmo(-1234.56) == CORES["negativo"]


def test_cor_por_sinal_none_retorna_cinza() -> None:
    """Valor None usa cor texto_sec (cinza) para não sugerir saúde."""
    assert _cor_por_sinal_ritmo(None) == CORES["texto_sec"]


def test_cor_por_sinal_zero_retorna_cinza() -> None:
    """Zero é tratado como neutro; não fingimos saudável sem ritmo real."""
    assert _cor_por_sinal_ritmo(0.0) == CORES["texto_sec"]


def test_metric_html_positivo_embute_cor_verde_e_valor_formatado() -> None:
    """HTML custom usa cor verde para valor positivo e formata BRL."""
    html = _metric_ritmo_html("Ritmo 3 meses", 2_500.0)
    assert CORES["positivo"] in html
    assert "Ritmo 3 meses" in html
    # Formatação BRL canônica do projeto -> contém vírgula decimal.
    assert "2.500" in html or "2500" in html


def test_metric_html_negativo_embute_cor_vermelha() -> None:
    """HTML custom usa cor vermelha para valor negativo."""
    html = _metric_ritmo_html("Ritmo histórico", -850.25)
    assert CORES["negativo"] in html


def test_metric_html_none_embute_cor_cinza_e_texto_explicativo() -> None:
    """HTML custom com None usa cinza e exibe texto 'Dados insuficientes'."""
    html = _metric_ritmo_html("Ritmo 12 meses", None)
    assert CORES["texto_sec"] in html
    assert "Dados insuficientes" in html


def test_metric_html_contem_hierarquia_visual_label_e_valor() -> None:
    """O HTML tem dois <p>: um com label pequeno, outro com valor grande."""
    html = _metric_ritmo_html("Teste", 100.0)
    # Label em fonte mínima, valor em 28px.
    assert "28px" in html
    assert "<p" in html


# "Cor comunica status mais rápido que número." -- princípio de scanner visual
