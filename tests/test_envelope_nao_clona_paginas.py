"""Testes de regressão -- engine de envelope NÃO clona PDF inteiro como páginas.

Sprint 98-1 (achado colateral da Sprint 98). Diagnóstico de superfície:
13 holerites G4F únicos por SHA-256 viraram 91 cópias bit-a-bit em
`data/raw/andre/itau_cc/` e `data/raw/andre/santander_cartao/`. Padrão:
`BANCARIO_ITAU_CC_<sha>.pdf` + `_1.pdf` ... `_6.pdf`, todos com SHA
identico e mesmo size (63419 bytes para o exemplo).

Investigação empírica concluiu que a engine atual de envelope (`expandir_pdf_multipage`,
Sprint 41d) está correta -- páginas individuais têm SHAs distintos, comprovado
por fixture sintética multi-página. Os 91 clones são RESÍDUO HISTÓRICO de:

  1. Pré-Sprint 90a: classifier roteava holerite G4F como `bancario_itau_cc` por
     menção a "ITAÚ UNIBANCO" no rodapé do contracheque (hoje a regra
     `holerite` em prioridade `especifico` derruba esse falso-positivo).
  2. Pré-Sprint 41 P2.3: `_resolver_destino_sem_colisao` ainda não fazia
     dedupe por SHA-256 -- reprocessamentos do mesmo arquivo viravam
     `_1.pdf`, `_2.pdf`, ..., `_6.pdf`.

Estes testes garantem que ambas as proteções continuam ativas para qualquer
PDF que entre via `--inbox` no futuro:

  - PDF multi-página com classificações distintas por página gera artefatos
    com SHAs distintos (engine não copia o original N vezes).
  - Re-rotear o mesmo artefato com mesmo conteúdo é idempotente: NÃO cria
    `_1`, `_2`, ... (P2.3 ativa).
  - Re-rotear artefatos com conteúdos diferentes mas mesmo `nome_canonico`
    SÃO desambiguados via `_1`, `_2`, ... (comportamento legítimo de colisão).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from src.intake import extractors_envelope as env
from src.intake import router
from src.intake.classifier import Decisao

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def envelopes_em_tmp(tmp_path, monkeypatch):
    """Redireciona _ENVELOPES_BASE para tmp_path -- isolamento entre testes."""
    monkeypatch.setattr(env, "_ENVELOPES_BASE", tmp_path / "_envelopes")
    yield


@pytest.fixture
def pdf_3_paginas(tmp_path) -> Path:
    """Cria PDF sintético de 3 páginas, cada página com texto distinto."""
    pdf_path = tmp_path / "tres_paginas.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    for i in range(1, 4):
        c.drawString(100, 700, f"PAGINA {i} -- texto exclusivo {i * 100}")
        c.drawString(100, 650, f"Conteúdo da página número {i}, distinto.")
        c.showPage()
    c.save()
    return pdf_path


def _hash_arquivo(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decisao_canonica(pasta: Path, nome: str = "DOC_aabbccdd.pdf") -> Decisao:
    return Decisao(
        tipo="docx",
        prioridade="normal",
        match_mode=None,
        extrator_modulo=None,
        origem_sprint="teste",
        pasta_destino=pasta,
        nome_canonico=nome,
        data_detectada_iso=None,
        regras_avaliadas=0,
    )


# ============================================================================
# Engine: expandir_pdf_multipage gera artefatos com SHAs distintos
# ============================================================================


def test_expandir_pdf_multipage_gera_paginas_com_shas_distintos(pdf_3_paginas):
    """Regressão: engine NÃO copia o PDF inteiro N vezes."""
    sha_original = _hash_arquivo(pdf_3_paginas)

    resultado = env.expandir_pdf_multipage(pdf_3_paginas)

    assert len(resultado.artefatos) == 3
    assert resultado.erros == []

    # Cada página tem conteúdo distinto -> SHA distinto
    shas_paginas = [_hash_arquivo(p) for p in resultado.artefatos]
    assert len(set(shas_paginas)) == 3, (
        f"Esperado 3 SHAs distintos, obtido {len(set(shas_paginas))}: {shas_paginas}"
    )

    # Nenhuma página tem o SHA do PDF original (proteção contra "cópia inteira")
    assert sha_original not in shas_paginas, (
        "Página gerada tem SHA do PDF original -- engine clonou em vez de fatiar"
    )

    # Tamanhos das páginas individuais devem ser MENORES que o original
    size_original = pdf_3_paginas.stat().st_size
    for pagina in resultado.artefatos:
        assert pagina.stat().st_size < size_original, (
            f"Página {pagina.name} tem {pagina.stat().st_size}b "
            f">= original {size_original}b (suspeita de clone)"
        )


def test_expandir_pdf_uma_pagina_gera_um_artefato_distinto_do_original(tmp_path):
    """PDF de 1 página: engine ainda cria artefato em pdf_split (padroniza pipeline)."""
    pdf_single = tmp_path / "single.pdf"
    c = canvas.Canvas(str(pdf_single), pagesize=letter)
    c.drawString(100, 700, "Pagina única teste")
    c.showPage()
    c.save()

    resultado = env.expandir_pdf_multipage(pdf_single)
    assert len(resultado.artefatos) == 1
    # Pode até bater por coincidência (1 pg in == 1 pg out), mas o caminho do
    # artefato JAMAIS é o caminho do original -- garante isolamento.
    assert resultado.artefatos[0] != pdf_single


# ============================================================================
# Router: idempotência por conteúdo (P2.3)
# ============================================================================


def test_rotear_artefato_mesmo_conteudo_nao_cria_clone_n(tmp_path):
    """Regressão P2.3: re-rotear artefato com SHA já existente no destino é idempotente.

    Cenário do achado: pré-P2.3, este teste produzia `_1.pdf` para o segundo
    artefato mesmo sendo conteúdo idêntico. Hoje deve produzir 1 só arquivo.
    """
    pasta_destino = tmp_path / "destino"
    pasta_destino.mkdir()

    # Criar dois "artefatos" com mesmo conteúdo, em paths distintos
    conteudo = "%PDF-1.4 conteúdo identico para os dois artefatos".encode()
    arq1 = tmp_path / "split1" / "pg1.pdf"
    arq2 = tmp_path / "split2" / "pg1.pdf"
    arq1.parent.mkdir()
    arq2.parent.mkdir()
    arq1.write_bytes(conteudo)
    arq2.write_bytes(conteudo)

    decisao = _decisao_canonica(pasta_destino, nome="DOC_aabbccdd.pdf")

    r1 = router.rotear_artefato(arq1, decisao)
    r2 = router.rotear_artefato(arq2, decisao)

    assert r1.sucesso and r2.sucesso

    arquivos_no_destino = list(pasta_destino.iterdir())
    assert len(arquivos_no_destino) == 1, (
        f"Esperado 1 arquivo único, obtido {len(arquivos_no_destino)}: "
        f"{[f.name for f in arquivos_no_destino]}. Regressão P2.3."
    )
    assert arquivos_no_destino[0].name == "DOC_aabbccdd.pdf"
    # Sem clones com sufixo _1, _2, ...
    nomes = {f.name for f in arquivos_no_destino}
    assert not any("_1" in n or "_2" in n for n in nomes), (
        f"Arquivos com sufixo _1/_2 detectados: {nomes}"
    )


def test_rotear_artefato_conteudos_diferentes_continuam_desambiguando(tmp_path):
    """Sanidade: P2.3 NÃO regride o caso legítimo de colisão por conteúdos distintos."""
    pasta_destino = tmp_path / "destino"
    pasta_destino.mkdir()

    arq1 = tmp_path / "a" / "pg1.pdf"
    arq2 = tmp_path / "b" / "pg1.pdf"
    arq1.parent.mkdir()
    arq2.parent.mkdir()
    arq1.write_bytes("%PDF-1.4 conteúdo distinto VERSAO A".encode())
    arq2.write_bytes("%PDF-1.4 conteúdo distinto VERSAO B".encode())

    decisao = _decisao_canonica(pasta_destino, nome="DOC_aabbccdd.pdf")
    r1 = router.rotear_artefato(arq1, decisao)
    r2 = router.rotear_artefato(arq2, decisao)

    assert r1.sucesso and r2.sucesso
    nomes = sorted(f.name for f in pasta_destino.iterdir())
    assert nomes == ["DOC_aabbccdd.pdf", "DOC_aabbccdd_1.pdf"], (
        f"Esperado desambiguação _1 para conteúdo distinto, obtido: {nomes}"
    )


def test_rotear_lote_pdf_multipagina_gera_um_arquivo_por_pagina(tmp_path, pdf_3_paginas):
    """Cenário ponta-a-ponta: PDF de 3 páginas com mesmo nome canônico para
    todas (cenário legítimo: extrator bancário emite mesmo template) NÃO
    deve consolidar em 1 só -- conteúdos distintos, _1 e _2 esperados.
    """
    resultado_envelope = env.expandir_pdf_multipage(pdf_3_paginas)
    assert len(resultado_envelope.artefatos) == 3

    pasta_destino = tmp_path / "extratos"
    decisao = _decisao_canonica(pasta_destino, nome="EXTRATO_aabbccdd.pdf")
    pares = [(art, decisao) for art in resultado_envelope.artefatos]

    relatorio = router.rotear_lote(
        arquivo_inbox=pdf_3_paginas,
        sha8_envelope=resultado_envelope.sha8_envelope,
        diretorio_envelope=resultado_envelope.diretorio_envelope,
        pares_artefato_decisao=pares,
        erros_envelope=[],
    )

    assert all(a.sucesso for a in relatorio.artefatos)
    arquivos = sorted(f.name for f in pasta_destino.iterdir())
    assert arquivos == [
        "EXTRATO_aabbccdd.pdf",
        "EXTRATO_aabbccdd_1.pdf",
        "EXTRATO_aabbccdd_2.pdf",
    ], f"Esperado 3 arquivos com sufixos _1, _2 (páginas distintas), obtido: {arquivos}"

    # E -- segurança contra o bug original -- nenhum dos 3 tem SHA do PDF inteiro
    sha_original = _hash_arquivo(pdf_3_paginas)
    for nome in arquivos:
        sha = _hash_arquivo(pasta_destino / nome)
        assert sha != sha_original, (
            f"{nome} tem SHA do PDF original -- regressão da engine de envelope"
        )


# "Confiar é bom; provar com fixture é melhor." -- princípio empírico
