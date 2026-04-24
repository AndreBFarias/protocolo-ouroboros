"""Sprint 92a.9: testes da barra de progresso inline dos cards de Metas."""

from __future__ import annotations

from src.dashboard.paginas.metas import _card_meta, _progress_inline_html


def test_progress_inline_html_rende_porcentagem_correta() -> None:
    """A largura da barra preenchida espelha o percentual fornecido."""
    html = _progress_inline_html(0.75, "#50FA7B")
    assert "width: 75.0%" in html
    assert "#50FA7B" in html
    assert "height: 4px" in html
    assert "border-radius: 2px" in html


def test_progress_inline_html_clampa_abaixo_de_zero() -> None:
    """Percentual negativo é clampado para 0."""
    html = _progress_inline_html(-0.2, "#FF5555")
    assert "width: 0.0%" in html


def test_progress_inline_html_clampa_acima_de_um() -> None:
    """Percentual maior que 1 é clampado para 100%."""
    html = _progress_inline_html(1.5, "#50FA7B")
    assert "width: 100.0%" in html


def test_progress_inline_html_usa_dracula_sobre_trilho_transparente() -> None:
    """Trilho de fundo usa rgba translúcido para não competir com o card."""
    html = _progress_inline_html(0.5, "#FFB86C")
    assert "rgba(" in html.lower()


def test_card_meta_monetaria_embute_progresso_inline() -> None:
    """Sprint 92a.9: barra aparece DENTRO do card, não como widget separado."""
    meta = {
        "nome": "Reserva de emergência",
        "prazo": "2026-12",
        "prioridade": 1,
        "tipo": "valor",
        "valor_alvo": 10_000.0,
        "valor_atual": 7_500.0,
    }
    html = _card_meta(meta)
    # Barra dentro do HTML do card (não fora).
    assert "height: 4px" in html
    # Percentual exato: 75%.
    assert "width: 75.0%" in html


def test_card_meta_binaria_nao_tem_progresso_inline() -> None:
    """Metas binárias (Sim/Não) não têm barra de progresso."""
    meta = {
        "nome": "Assinar contrato",
        "prazo": "2026-06",
        "prioridade": 2,
        "tipo": "binario",
    }
    html = _card_meta(meta)
    # Binária não deve renderizar a barra de 4px.
    assert "height: 4px" not in html


def test_card_meta_cor_por_status_positivo_quando_100() -> None:
    """Meta 100% completa usa cor positivo Dracula (#50FA7B)."""
    meta = {
        "nome": "Completa",
        "prazo": "2026-12",
        "prioridade": 3,
        "tipo": "valor",
        "valor_alvo": 1000.0,
        "valor_atual": 1000.0,
    }
    html = _card_meta(meta)
    assert "#50FA7B" in html or "#50fa7b" in html.lower()


def test_card_meta_cor_por_status_negativo_quando_baixo() -> None:
    """Meta abaixo de 50% usa cor negativo (#FF5555)."""
    meta = {
        "nome": "Inicio",
        "prazo": "2026-12",
        "prioridade": 3,
        "tipo": "valor",
        "valor_alvo": 1000.0,
        "valor_atual": 100.0,
    }
    html = _card_meta(meta)
    assert "#FF5555" in html or "#ff5555" in html.lower()


# "Progresso invisível não motiva ninguém." -- princípio de feedback visual
