"""Prova de fogo da Sprint 41: roda o orquestrador real contra os 2 PDFs da
inbox em ambiente isolado (tmp), imprime RelatorioRoteamento detalhado.

NÃO toca em `inbox/` real -- copia os arquivos para um diretório temporário,
redireciona TODAS as constantes de path para esse temp, e mostra o que o
pipeline DETERMINÍSTICO faria. Sem rede, sem IA, sem dependência de
serviço externo.

Uso:

    .venv/bin/python scripts/sprint41_prova_fogo.py

Output: tabela por arquivo da inbox + estatísticas finais. Diretório
temporário é descartado ao final, mas todos os caminhos são impressos
para o supervisor inspecionar antes do cleanup (--keep para manter).

Critério de aprovação (alinhado no chat):

- pdf_notas.pdf: 3 páginas -> 3 cupons garantia em garantias_estendidas/
- notas de garantia e compras.pdf: 4 páginas (todas SCAN sem OCR aqui) ->
  4 vão para _classificar/ (estado correto, OCR de PDF é Sprint 45)

Quando 45 estiver pronta e os scans forem OCRzados antes da classificação,
o segundo PDF roteia 2 NFC-e + 2 cupons garantia.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

# Permite invocar como `python scripts/sprint41_prova_fogo.py` sem instalação
_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ))

from src.intake import classifier as clf  # noqa: E402
from src.intake import extractors_envelope as env  # noqa: E402
from src.intake import orchestrator as orq  # noqa: E402
from src.intake import router  # noqa: E402
from src.intake.router import RelatorioRoteamento  # noqa: E402

INBOX_REAL = _RAIZ / "inbox"
ARQUIVOS_REAIS = [
    INBOX_REAL / "pdf_notas.pdf",
    INBOX_REAL / "notas de garantia e compras.pdf",
]


def isolar_paths(raiz_temp: Path) -> None:
    """Redireciona todas as constantes de path do intake para raiz_temp."""
    env._ENVELOPES_BASE = raiz_temp / "data" / "raw" / "_envelopes"
    router._RAIZ_REPO = raiz_temp
    router._ORIGINAIS_BASE = raiz_temp / "data" / "raw" / "_envelopes" / "originais"
    clf._RAIZ_REPO = raiz_temp
    clf._PATH_DATA_RAW = raiz_temp / "data" / "raw"
    clf.recarregar_tipos()


def imprimir_relatorio(relatorio: RelatorioRoteamento, raiz_temp: Path) -> None:
    """Tabela legível por humano. Caminhos relativos a raiz_temp pra leitura."""
    print()
    print("=" * 90)
    print(f"ARQUIVO: {relatorio.arquivo_inbox.name}")
    print(f"sha8: {relatorio.sha8_envelope}")
    print(f"copia auditoria: {_rel(relatorio.copia_original, raiz_temp)}")
    print(f"sucesso_total: {relatorio.sucesso_total}")
    print(f"erros do envelope ({len(relatorio.erros)}):")
    for e in relatorio.erros:
        print(f"  - {e}")
    print()
    print(f"  {'#':<3} {'TIPO':<28} {'PRIORIDADE':<11} {'OK':<4} {'DESTINO'}")
    print(f"  {'-' * 3} {'-' * 28} {'-' * 11} {'-' * 4} {'-' * 50}")
    for i, a in enumerate(relatorio.artefatos, start=1):
        tipo = a.decisao.tipo or "_NAO_CLASSIFICADO_"
        prioridade = a.decisao.prioridade or "-"
        ok = "OK" if a.sucesso else "FAIL"
        destino = _rel(a.caminho_final, raiz_temp)
        print(f"  {i:<3} {tipo:<28} {prioridade:<11} {ok:<4} {destino}")
        if a.motivo:
            print(f"      motivo: {a.motivo}")
        if a.decisao.data_detectada_iso:
            print(f"      data: {a.decisao.data_detectada_iso}")
    print()


def _rel(caminho: Path, raiz_temp: Path) -> str:
    try:
        return f"<temp>/{caminho.relative_to(raiz_temp)}"
    except ValueError:
        return str(caminho)


_EXTENSOES_INTERESSANTES: tuple[str, ...] = (
    ".pdf",
    ".csv",
    ".xml",
    ".zip",
    ".eml",
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".heif",
    ".webp",
    ".xls",
    ".xlsx",
    ".ofx",
    ".txt",
)


def coletar_arquivos_da_pasta(pasta: Path) -> list[Path]:
    """Varre `pasta` recursivamente e devolve arquivos com extensões úteis."""
    if not pasta.exists():
        return []
    return sorted(
        p for p in pasta.rglob("*") if p.is_file() and p.suffix.lower() in _EXTENSOES_INTERESSANTES
    )


def imprimir_resumo_agregado(relatorios: list[RelatorioRoteamento], raiz_temp: Path) -> None:
    """Resumo agregado: breakdown por tipo, lista de fallbacks, recall global."""
    contador_tipo: dict[str, int] = {}
    fallbacks: list[tuple[str, str]] = []  # (arquivo_inbox.name, motivo)
    erros_envelope: list[tuple[str, str]] = []
    total_artefatos = 0
    total_ok = 0

    for relatorio in relatorios:
        for erro in relatorio.erros:
            erros_envelope.append((relatorio.arquivo_inbox.name, erro))
        for art in relatorio.artefatos:
            total_artefatos += 1
            tipo = art.decisao.tipo or "_NAO_CLASSIFICADO_"
            contador_tipo[tipo] = contador_tipo.get(tipo, 0) + 1
            if art.sucesso:
                total_ok += 1
            else:
                fallbacks.append((relatorio.arquivo_inbox.name, art.motivo or "?"))

    print("=" * 90)
    print("RESUMO AGREGADO")
    print("=" * 90)
    print()
    print("Distribuição por tipo:")
    print(f"  {'TIPO':<32} {'QTD':>6}")
    print(f"  {'-' * 32} {'-' * 6}")
    for tipo, qtd in sorted(contador_tipo.items(), key=lambda x: -x[1]):
        print(f"  {tipo:<32} {qtd:>6}")
    print()
    print(f"Total de arquivos da inbox:  {len(relatorios)}")
    print(f"Total de artefatos gerados:  {total_artefatos}")
    print(f"Roteados (pasta canônica):   {total_ok}")
    print(f"Em _classificar/:            {total_artefatos - total_ok}")
    if total_artefatos:
        print(f"Recall global:               {total_ok / total_artefatos * 100:.0f}%")
    if erros_envelope:
        print()
        print(f"Erros de envelope ({len(erros_envelope)}):")
        for arquivo, erro in erros_envelope[:10]:
            print(f"  - {arquivo}: {erro}")
        if len(erros_envelope) > 10:
            print(f"  ... e mais {len(erros_envelope) - 10}")
    if fallbacks:
        print()
        print(f"Amostras de fallback (_classificar/) - primeiras 15 de {len(fallbacks)}:")
        for arquivo, motivo in fallbacks[:15]:
            print(f"  - {arquivo}: {motivo[:60]}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="manter o diretório temporário após execução (para inspeção)",
    )
    parser.add_argument(
        "--pessoa", default="andre", help="pessoa para resolver pasta_destino_template"
    )
    parser.add_argument(
        "--pasta",
        type=Path,
        default=None,
        help=(
            "varre uma pasta recursivamente como fonte (alternativa aos 2 PDFs fixos da inbox/). "
            "Útil para validar contra histórico em data/raw/. Imprime resumo agregado em vez do detalhado."
        ),
    )
    args = parser.parse_args()

    if args.pasta:
        origens = coletar_arquivos_da_pasta(args.pasta)
        if not origens:
            print(f"ERRO: pasta {args.pasta} sem arquivos elegíveis", file=sys.stderr)
            return 1
        modo = "pasta"
    else:
        faltando = [p for p in ARQUIVOS_REAIS if not p.exists()]
        if faltando:
            print(
                "ERRO: arquivos reais da inbox/ não encontrados:",
                *[f"  - {p}" for p in faltando],
                sep="\n",
            )
            return 1
        origens = ARQUIVOS_REAIS
        modo = "fixo"

    raiz_temp = Path(tempfile.mkdtemp(prefix="sprint41_prova_"))
    print(f"Raiz temporária: {raiz_temp}")
    print(f"Pessoa:          {args.pessoa}")
    print(f"Modo:            {modo}")
    print(f"Origens:         {len(origens)} arquivo(s)")
    if args.pasta:
        print(f"Pasta varrida:   {args.pasta}")
    print()

    try:
        isolar_paths(raiz_temp)

        # Copia origens para uma pseudo-inbox plana dentro do tmp (resolve colisões)
        pseudo_inbox = raiz_temp / "inbox"
        pseudo_inbox.mkdir(parents=True, exist_ok=True)
        copias: list[Path] = []
        for original in origens:
            destino_base = pseudo_inbox / original.name
            destino = destino_base
            contador = 1
            while destino.exists():
                destino = pseudo_inbox / f"{destino_base.stem}_{contador}{destino_base.suffix}"
                contador += 1
            shutil.copy2(original, destino)
            copias.append(destino)
        print(f"Copiados para pseudo-inbox: {len(copias)}")
        print()

        # Processa cada arquivo via orquestrador real
        relatorios: list[RelatorioRoteamento] = []
        falhas_processamento: list[tuple[Path, str]] = []
        for copia in copias:
            try:
                relatorio = orq.processar_arquivo_inbox(copia, pessoa=args.pessoa)
                relatorios.append(relatorio)
            except Exception as exc:  # noqa: BLE001 -- queremos relatar tudo
                falhas_processamento.append((copia, repr(exc)))

        if modo == "fixo":
            for relatorio in relatorios:
                imprimir_relatorio(relatorio, raiz_temp)

        if falhas_processamento:
            print("=" * 90)
            print(f"FALHAS DE PROCESSAMENTO ({len(falhas_processamento)})")
            print("=" * 90)
            for caminho, erro in falhas_processamento[:10]:
                print(f"  - {caminho.name}: {erro}")
            print()

        imprimir_resumo_agregado(relatorios, raiz_temp)

        if args.keep:
            print(f"Diretório mantido para inspeção: {raiz_temp}")
        else:
            print("Removendo diretório temporário (use --keep para manter)...")
            shutil.rmtree(raiz_temp)
    except Exception:
        import traceback

        traceback.print_exc()
        print(f"\nDiretório temporário PRESERVADO para debug: {raiz_temp}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# "A prova do pão é comê-lo." -- Cervantes
