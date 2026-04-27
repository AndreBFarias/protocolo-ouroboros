"""Testes de dedupe por hash no roteamento (P2.3 2026-04-23).

Origem: auditoria 2026-04-23 detectou Itaú 5 extratos únicos -> 29 arquivos
físicos (5.8x cada) e Santander 18 -> 102 (5.7x). O roteador aplicava
desambiguação `_1`, `_2`, ... sem checar se o conteúdo era o mesmo,
acumulando cópias literais a cada re-ingestão.

Agora `_resolver_destino_sem_colisao` aceita `arquivo_origem` opcional:
- Destino existente com mesmo hash SHA-256 -> retorna destino (pula copia).
- Destino existente com hash diferente -> aplica desambiguacao `_1`.
"""

from __future__ import annotations

from pathlib import Path

from src.intake.extractors_envelope import _resolver_destino_sem_colisao


class TestResolverDestinoComHash:
    def test_destino_inexistente_devolve_nome_original(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "origem" / "extrato.pdf"
        arquivo.parent.mkdir()
        arquivo.write_bytes(b"conteudo")
        destino_dir = tmp_path / "dest"
        destino_dir.mkdir()

        r = _resolver_destino_sem_colisao(destino_dir, "extrato.pdf", arquivo_origem=arquivo)
        assert r == destino_dir / "extrato.pdf"

    def test_destino_existe_com_mesmo_hash_devolve_destino(self, tmp_path: Path) -> None:
        conteudo = b"x" * 1000
        arquivo = tmp_path / "origem" / "extrato.pdf"
        arquivo.parent.mkdir()
        arquivo.write_bytes(conteudo)
        destino_dir = tmp_path / "dest"
        destino_dir.mkdir()
        (destino_dir / "extrato.pdf").write_bytes(conteudo)

        r = _resolver_destino_sem_colisao(destino_dir, "extrato.pdf", arquivo_origem=arquivo)
        # Idempotência: destino existente com mesmo hash é reaproveitado
        assert r == destino_dir / "extrato.pdf"

    def test_destino_existe_com_hash_diferente_desambigua(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "origem" / "extrato.pdf"
        arquivo.parent.mkdir()
        arquivo.write_bytes(b"conteudo_novo")
        destino_dir = tmp_path / "dest"
        destino_dir.mkdir()
        (destino_dir / "extrato.pdf").write_bytes(b"conteudo_existente")

        r = _resolver_destino_sem_colisao(destino_dir, "extrato.pdf", arquivo_origem=arquivo)
        # Conteúdos distintos -> desambiguação canônica
        assert r == destino_dir / "extrato_1.pdf"

    def test_sem_arquivo_origem_mantem_comportamento_antigo(self, tmp_path: Path) -> None:
        destino_dir = tmp_path / "dest"
        destino_dir.mkdir()
        (destino_dir / "a.pdf").write_bytes(b"x")
        # Sem arquivo_origem = comportamento antigo (assume conteúdo distinto)
        r = _resolver_destino_sem_colisao(destino_dir, "a.pdf")
        assert r == destino_dir / "a_1.pdf"

    def test_multiplas_copias_encontra_idempotencia_em_N(self, tmp_path: Path) -> None:
        """Já temos extrato.pdf, extrato_1.pdf, extrato_2.pdf com conteúdos
        distintos. Quando chega nova ingestão do mesmo conteúdo que extrato_2,
        a função deve devolver extrato_2.pdf (não criar extrato_3)."""
        destino_dir = tmp_path / "dest"
        destino_dir.mkdir()
        (destino_dir / "extrato.pdf").write_bytes(b"A")
        (destino_dir / "extrato_1.pdf").write_bytes(b"B")
        (destino_dir / "extrato_2.pdf").write_bytes(b"C")

        arquivo = tmp_path / "origem" / "extrato.pdf"
        arquivo.parent.mkdir()
        arquivo.write_bytes(b"C")

        r = _resolver_destino_sem_colisao(destino_dir, "extrato.pdf", arquivo_origem=arquivo)
        assert r == destino_dir / "extrato_2.pdf"
