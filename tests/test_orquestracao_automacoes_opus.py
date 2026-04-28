"""Sprint 108: testes regressivos da orquestracao das automacoes Opus.

Cobre:
  1. run.sh --full-cycle inclui as 3 automacoes (dedup, migrar_pessoa, backfill).
  2. run.sh --reextrair-tudo inclui as automacoes ANTES da reextracao.
  3. menu_interativo opção 7 esta no dispatcher.
  4. docs/AUTOMACOES_OPUS.md documenta a cadeia.
"""

from __future__ import annotations

from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]


def test_run_sh_full_cycle_inclui_automacoes():
    run_sh = (_RAIZ / "run.sh").read_text(encoding="utf-8")
    # Encontra o bloco --full-cycle
    idx = run_sh.find("--full-cycle)")
    assert idx > 0, "bloco --full-cycle não encontrado em run.sh"
    bloco = run_sh[idx : idx + 2000]
    assert "dedup_classificar" in bloco
    assert "migrar_pessoa_via_cpf" in bloco
    assert "backfill_arquivo_origem" in bloco


def test_run_sh_reextrair_tudo_inclui_automacoes_antes_reextracao():
    run_sh = (_RAIZ / "run.sh").read_text(encoding="utf-8")
    idx = run_sh.find("--reextrair-tudo)")
    assert idx > 0, "bloco --reextrair-tudo não encontrado"
    bloco = run_sh[idx : idx + 2500]
    pos_dedup = bloco.find("dedup_classificar")
    pos_migrar = bloco.find("migrar_pessoa_via_cpf")
    pos_backfill = bloco.find("backfill_arquivo_origem")
    # Procura o comando real (não o comentário). O comando tem 'reprocessar_documentos'.
    pos_reextrair = bloco.find("reprocessar_documentos --forcar-reextracao")
    assert all(p > 0 for p in (pos_dedup, pos_migrar, pos_backfill, pos_reextrair))
    # Automacoes vem ANTES da reextracao
    assert pos_dedup < pos_reextrair
    assert pos_migrar < pos_reextrair
    assert pos_backfill < pos_reextrair


def test_run_sh_helper_run_passo_definido():
    run_sh = (_RAIZ / "run.sh").read_text(encoding="utf-8")
    assert "run_passo() {" in run_sh
    assert "logs/auditoria_opus.log" in run_sh


def test_menu_interativo_opcao_7_auditoria_opus():
    menu = (_RAIZ / "scripts" / "menu_interativo.py").read_text(encoding="utf-8")
    assert '"7":' in menu
    assert "Auditoria Opus" in menu
    assert '"7": _acao_auditoria_opus' in menu


def test_doc_automacoes_opus_existe():
    doc = _RAIZ / "docs" / "AUTOMACOES_OPUS.md"
    assert doc.exists()
    conteudo = doc.read_text(encoding="utf-8")
    assert "Sprint 108" in conteudo
    assert "dedup_classificar" in conteudo
    assert "migrar_pessoa_via_cpf" in conteudo
    assert "backfill_arquivo_origem" in conteudo


# "Sequencia que se executa sozinha eh sequencia que vira invariante." -- principio anti-débito
