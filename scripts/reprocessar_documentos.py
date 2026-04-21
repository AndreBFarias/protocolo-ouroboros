"""Reprocessar todos os documentos em data/raw/ e popular o grafo (Sprint 57).

Auditoria 2026-04-21 revelou que as Sprints 47a, 47b, 48, 49 e 50 foram
declaradas concluídas com pytest verde mas o grafo runtime ficou quase vazio
(2 documentos, 33 itens, 0 arestas documento_de / prescreve_cobre / mesmo_produto_que).
Plumbing existe -- faltava invocar os extratores contra os arquivos reais.

Este script:

  1. Varre data/raw/**/*.{pdf,xml,jpg,jpeg,png,heic,eml} (CSV/OFX/XLSX ficam de
     fora: não viram documentos no grafo -- são extratos bancários consumidos
     pelo pipeline principal).
  2. Para cada arquivo, detecta tipo via src/intake/registry.py:detectar_tipo
     (que consolida file_detector legado + classifier YAML).
  3. Instancia o extrator documental apropriado (DANFE, NFC-e, XML NFe, cupom
     de garantia estendida, receita médica, garantia de fabricante, cupom
     térmico fotografado, recibo não-fiscal) passando uma instância única de
     GrafoDB para evitar abrir/fechar conexão por arquivo.
  4. Chama extrator.extrair() -- o efeito colateral ingere no grafo via
     ingerir_documento_fiscal / ingerir_prescricao / ingerir_garantia /
     ingerir_apolice.
  5. Ao final, replica os passos 12-14 do pipeline principal:
       - linkar_documentos_a_transacoes (Sprint 48, aresta `documento_de`)
       - executar_er_produtos (Sprint 49, aresta `mesmo_produto_que`)
       - categorizar_todos_items_no_grafo (Sprint 50, aresta `categoria_de`)

Flags:

    --dry-run : apenas lista o que seria ingerido. Não abre GrafoDB.
    --raiz    : caminho raiz alternativo de data/raw (default: data/raw).
    --grafo   : caminho alternativo para grafo.sqlite.

Nota importante sobre a aresta de linking documento-transação (Sprint 48):
o spec original da Sprint 57 cita `pago_com`, mas a implementação canônica
da Sprint 48 em src/graph/linking.py usa `documento_de`. O script e o teste
usam o nome canônico do código (`documento_de`) e o sumário explica a
divergência para que o supervisor saiba rastrear.

Armadilhas A57-1/2/3 respeitadas:
  - Nunca move originais (só lê).
  - Passa grafo compartilhado -> idempotência natural (chave_44 única etc.).
  - Reporta honestamente 0 arquivos por pasta vazia -- não inventa dado.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

# Garante que `src.*` seja importavel quando rodado via `.venv/bin/python scripts/...`.
_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
if str(_RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPO))

from src.extractors.cupom_garantia_estendida_pdf import ExtratorCupomGarantiaEstendida
from src.extractors.cupom_termico_foto import ExtratorCupomTermicoFoto
from src.extractors.danfe_pdf import ExtratorDanfePDF
from src.extractors.garantia import ExtratorGarantiaFabricante
from src.extractors.nfce_pdf import ExtratorNfcePDF
from src.extractors.receita_medica import ExtratorReceitaMedica
from src.extractors.recibo_nao_fiscal import ExtratorReciboNaoFiscal
from src.extractors.xml_nfe import ExtratorXmlNFe
from src.graph.db import GrafoDB, caminho_padrao
from src.intake.orchestrator import detectar_mime
from src.intake.preview import gerar_preview
from src.intake.registry import detectar_tipo
from src.utils.logger import configurar_logger

logger = configurar_logger("scripts.reprocessar_documentos")


EXTENSOES_DOCUMENTAIS: set[str] = {
    ".pdf",
    ".xml",
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".heif",
    ".eml",
    ".zip",
}

# Ordem importa: extratores mais especificos ANTES do catch-all
# recibo_nao_fiscal. Mesma ordem declarada em src/pipeline.py:_descobrir_extratores
# (trecho documental).
EXTRATORES_DOCUMENTAIS: tuple[type, ...] = (
    ExtratorCupomGarantiaEstendida,  # apolice SUSEP (Sprint 47c)
    ExtratorNfcePDF,                 # NFC-e modelo 65 (Sprint 44b)
    ExtratorDanfePDF,                # DANFE modelo 55 (Sprint 44)
    ExtratorCupomTermicoFoto,        # cupom fotografado (Sprint 45)
    ExtratorXmlNFe,                  # XML NFe (Sprint 46)
    ExtratorReceitaMedica,           # receita medica (Sprint 47a)
    ExtratorGarantiaFabricante,      # garantia de fabricante (Sprint 47b)
    ExtratorReciboNaoFiscal,         # catch-all (Sprint 47)
)


def _escanear(raiz: Path) -> list[Path]:
    """Lista arquivos documentais em `raiz` (recursivo)."""
    if not raiz.exists():
        logger.warning("raiz inexistente: %s", raiz)
        return []

    arquivos: list[Path] = []
    for caminho in raiz.rglob("*"):
        if not caminho.is_file():
            continue
        if caminho.suffix.lower() not in EXTENSOES_DOCUMENTAIS:
            continue
        # Ignora duplicatas de download "(1)" "(2)"
        if " (1)" in caminho.stem or " (2)" in caminho.stem:
            continue
        arquivos.append(caminho)
    return sorted(arquivos)


def _detectar(caminho: Path) -> tuple[str, str | None]:
    """Devolve (tipo_detectado, extrator_modulo) -- robusto a falha de preview."""
    try:
        mime = detectar_mime(caminho)
    except Exception as erro:  # noqa: BLE001 -- best-effort
        logger.debug("falha mime em %s: %s", caminho.name, erro)
        mime = "application/octet-stream"

    preview: str | None
    try:
        preview = gerar_preview(caminho, mime)
    except Exception as erro:  # noqa: BLE001 -- best-effort
        logger.debug("falha preview em %s: %s", caminho.name, erro)
        preview = None

    try:
        decisao = detectar_tipo(caminho, mime, preview or "", pessoa="_indefinida")
    except Exception as erro:  # noqa: BLE001 -- best-effort
        logger.warning("falha detectar_tipo em %s: %s", caminho.name, erro)
        return ("_erro_deteccao", None)

    return (decisao.tipo or "_nao_classificado", decisao.extrator_modulo)


def _detectar_leve(caminho: Path) -> str:
    """Inferência rápida de tipo por path (não abre PDF).

    Usado no --dry-run para evitar pdfplumber/OCR em ~170 arquivos. A detecção
    real roda só no modo normal, onde cada extrator abre o arquivo uma única
    vez para pode_processar + extrair.
    """
    suf = caminho.suffix.lower()
    caminho_lower = str(caminho).lower()
    if suf == ".xml":
        return "xml_nfe"
    if "nfce" in caminho_lower:
        return "nfce_consumidor_eletronica"
    if "danfe" in caminho_lower or "nfs_fiscais" in caminho_lower:
        return "danfe_nfe55"
    if "garantias_estendidas" in caminho_lower:
        return "cupom_garantia_estendida"
    if "holerite" in caminho_lower or "contracheque" in caminho_lower:
        return "holerite"
    if "receita" in caminho_lower or "receituario" in caminho_lower or "prescricao" in caminho_lower:
        return "receita_medica"
    if "garantia" in caminho_lower and "estendida" not in caminho_lower:
        return "garantia_fabricante"
    if "cupom" in caminho_lower:
        return "cupom_fiscal_foto"
    if "santander" in caminho_lower:
        return "fatura_cartao"
    if "itau" in caminho_lower:
        return "extrato_bancario"
    if "_envelopes" in caminho_lower or "_classificar" in caminho_lower:
        return "_nao_classificado"
    return "_indeterminado"


def _ingerir_um(
    caminho: Path,
    grafo: GrafoDB,
) -> tuple[str, str | None]:
    """Tenta cada extrator documental no arquivo. Devolve (status, nome_classe).

    Status possíveis:
        "ingerido"     : extrator aceitou e .extrair() rodou sem exceção
        "sem_extrator" : nenhum extrator documental com pode_processar True
        "erro"         : pode_processar ou extrair levantou exceção
    """
    for cls in EXTRATORES_DOCUMENTAIS:
        # Nem todos aceitam grafo=... pelo mesmo kwarg, mas os 8 documentais
        # aceitam. Passar o grafo compartilhado evita que cada extrator abra e
        # feche conexão própria (~170 arquivos -> ~170 commits).
        try:
            extrator = cls(caminho, grafo=grafo)
        except Exception as erro:  # noqa: BLE001
            logger.error(
                "falha instanciar %s com %s: %s", cls.__name__, caminho.name, erro
            )
            continue

        try:
            aceita = extrator.pode_processar(caminho)
        except Exception as erro:  # noqa: BLE001
            logger.debug(
                "%s.pode_processar levantou em %s: %s", cls.__name__, caminho.name, erro
            )
            continue

        if not aceita:
            continue

        try:
            extrator.extrair()
        except Exception as erro:  # noqa: BLE001 -- não pode derrubar o lote
            logger.error(
                "%s.extrair falhou em %s: %s\n%s",
                cls.__name__,
                caminho.name,
                erro,
                traceback.format_exc(limit=3),
            )
            return ("erro", cls.__name__)

        return ("ingerido", cls.__name__)

    return ("sem_extrator", None)


def _rodar_fases_pos_ingestao(grafo: GrafoDB) -> dict[str, dict[str, int]]:
    """Replica os passos 12-14 do pipeline principal sobre o grafo já populado.

    12 -- Sprint 48: aresta `documento_de` (documento -> transação)
    13 -- Sprint 49: aresta `mesmo_produto_que` (item -> produto_canonico)
    14 -- Sprint 50: aresta `categoria_de` (item -> categoria)

    Devolve dict agregado com os stats de cada fase. Cada fase é independente
    e captura a própria exceção -- uma falha em 48 não impede 49/50.
    """
    stats: dict[str, dict[str, int]] = {}

    try:
        from src.graph.linking import linkar_documentos_a_transacoes
        stats["linking_48"] = linkar_documentos_a_transacoes(grafo)
    except Exception as erro:  # noqa: BLE001
        logger.warning("Sprint 48 (linking) falhou: %s", erro)
        stats["linking_48"] = {"erro": 1}

    try:
        from src.graph.er_produtos import executar_er_produtos
        stats["er_produtos_49"] = executar_er_produtos(grafo)
    except Exception as erro:  # noqa: BLE001
        logger.warning("Sprint 49 (ER produtos) falhou: %s", erro)
        stats["er_produtos_49"] = {"erro": 1}

    try:
        from src.transform.item_categorizer import categorizar_todos_items_no_grafo
        stats["item_categorizer_50"] = categorizar_todos_items_no_grafo(grafo)
    except Exception as erro:  # noqa: BLE001
        logger.warning("Sprint 50 (categorizer itens) falhou: %s", erro)
        stats["item_categorizer_50"] = {"erro": 1}

    return stats


def _contagem_grafo(grafo: GrafoDB) -> dict[str, int]:
    """Snapshot das contagens relevantes no grafo."""
    # GrafoDB expõe a conexão via atributo privado `_conn`; usamos como
    # contrato de leitura porque `listar_nodes`/`listar_edges` não agregam
    # COUNT e rodar N consultas completas seria caro em grafo grande.
    cur = grafo._conn.cursor()  # noqa: SLF001 -- leitura agregada
    tipos_node = (
        "documento",
        "item",
        "fornecedor",
        "prescricao",
        "garantia",
        "apolice",
        "transacao",
        "categoria",
        "periodo",  # noqa: accent
        "produto_canonico",
    )
    tipos_edge = (
        "contem_item",
        "fornecido_por",
        "ocorre_em",
        "documento_de",
        "prescreve_cobre",
        "cobre",
        "mesmo_produto_que",
        "categoria_de",
    )
    snap: dict[str, int] = {}
    for tipo in tipos_node:
        snap[f"node.{tipo}"] = cur.execute(
            "SELECT COUNT(*) FROM node WHERE tipo=?", (tipo,)
        ).fetchone()[0]
    for tipo in tipos_edge:
        snap[f"edge.{tipo}"] = cur.execute(
            "SELECT COUNT(*) FROM edge WHERE tipo=?", (tipo,)
        ).fetchone()[0]
    return snap


def _imprimir_sumario_dry_run(
    arquivos: list[Path],
    por_tipo: Counter,
    por_extrator: Counter,
    por_pasta: dict[str, int],
) -> None:
    print("=" * 72)
    print("DRY-RUN: nenhum node/edge foi criado; nenhum arquivo foi movido.")
    print("=" * 72)
    print(f"Arquivos encontrados: {len(arquivos)}")
    print()
    print("-- Por pasta (top 15):")
    for pasta, n in sorted(por_pasta.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {n:>4}  {pasta}")
    print()
    print("-- Por tipo detectado (inferência leve por path):")
    for tipo, n in por_tipo.most_common():
        print(f"  {n:>4}  {tipo}")
    print()
    print("-- Por extrator_modulo sugerido:")
    for extrator, n in por_extrator.most_common():
        print(f"  {n:>4}  {extrator}")


def _imprimir_sumario_execucao(
    arquivos: list[Path],
    por_status: Counter,
    por_extrator_usado: Counter,
    duracao_s: float,
    snap_antes: dict[str, int],
    snap_depois: dict[str, int],
    stats_pos: dict[str, dict[str, int]],
) -> None:
    print("=" * 72)
    print(f"Reprocessamento concluído em {duracao_s:.1f}s")
    print("=" * 72)
    print(f"Arquivos varridos:      {len(arquivos)}")
    print(f"  ingeridos (ok):       {por_status.get('ingerido', 0)}")
    print(f"  sem extrator:         {por_status.get('sem_extrator', 0)}")
    print(f"  erro:                 {por_status.get('erro', 0)}")
    print()
    print("-- Extratores acionados:")
    for extrator, n in por_extrator_usado.most_common():
        print(f"  {n:>4}  {extrator}")
    print()
    print("-- Grafo antes -> depois:")
    chaves = sorted(set(snap_antes) | set(snap_depois))
    for chave in chaves:
        antes = snap_antes.get(chave, 0)
        depois = snap_depois.get(chave, 0)
        delta = depois - antes
        seta = "->" if delta != 0 else "=="
        marca = " +" if delta > 0 else ("  " if delta == 0 else " -")
        print(f"  {chave:<28} {antes:>6} {seta} {depois:>6} {marca}{abs(delta)}")
    print()
    print("-- Fases pós-ingestão:")
    for fase, s in stats_pos.items():
        print(f"  {fase}:")
        for chave, valor in sorted(s.items()):
            print(f"      {chave} = {valor}")
    print()
    print("Nota: a aresta de linking documento<->transação é 'documento_de'")
    print("(Sprint 48, src/graph/linking.py), não 'pago_com'. O spec 57")
    print("cita 'pago_com' por convenção informal; o código canônico usa")
    print("'documento_de'.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reprocessa todos os documentos de data/raw e popula o grafo.",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Apenas lista o que seria ingerido; não abre grafo.")
    parser.add_argument("--raiz", type=Path, default=_RAIZ_REPO / "data" / "raw",
                        help="Raiz de data/raw (default: %(default)s).")
    parser.add_argument("--grafo", type=Path, default=None,
                        help="Caminho alternativo para grafo.sqlite.")
    args = parser.parse_args(argv)

    raiz: Path = args.raiz
    arquivos = _escanear(raiz)
    if not arquivos:
        print(f"0 arquivos documentais em {raiz}.")
        print("Coloque PDFs/XMLs em data/inbox/ e rode ./run.sh --inbox")
        print("para que o intake roteie cada um para data/raw/<pessoa>/<tipo>/.")
        print("Depois rode este script novamente.")
        return 0

    por_pasta: dict[str, int] = defaultdict(int)
    for arq in arquivos:
        try:
            relativo = arq.relative_to(raiz)
            # agrupa pela pasta imediata (pessoa/tipo) para o sumario
            chave = "/".join(relativo.parts[:-1]) or "."
        except ValueError:
            chave = str(arq.parent)
        por_pasta[chave] += 1

    if args.dry_run:
        logger.info(
            "Dry-run: deteccao leve por path de %d arquivo(s) (sem abrir PDF)",
            len(arquivos),
        )
        por_tipo: Counter = Counter()
        por_extrator: Counter = Counter()
        for arq in arquivos:
            tipo = _detectar_leve(arq)
            por_tipo[tipo] += 1
            # extrator_modulo sugerido e inferido a partir do tipo no modo leve
            mapa_tipo_extrator = {
                "xml_nfe": "src.extractors.xml_nfe",
                "nfce_consumidor_eletronica": "src.extractors.nfce_pdf",
                "danfe_nfe55": "src.extractors.danfe_pdf",
                "cupom_garantia_estendida": "src.extractors.cupom_garantia_estendida_pdf",
                "holerite": "src.extractors.contracheque_pdf",
                "receita_medica": "src.extractors.receita_medica",
                "garantia_fabricante": "src.extractors.garantia",
                "cupom_fiscal_foto": "src.extractors.cupom_termico_foto",
                "fatura_cartao": "src.extractors.santander_pdf",
                "extrato_bancario": "src.extractors.itau_pdf",
            }
            por_extrator[mapa_tipo_extrator.get(tipo, "<null>")] += 1
        _imprimir_sumario_dry_run(arquivos, por_tipo, por_extrator, por_pasta)
        return 0

    caminho_grafo = args.grafo or caminho_padrao()
    logger.info("Grafo alvo: %s", caminho_grafo)
    grafo = GrafoDB(caminho_grafo)
    try:
        grafo.criar_schema()
        snap_antes = _contagem_grafo(grafo)

        por_status: Counter = Counter()
        por_extrator_usado: Counter = Counter()
        inicio = time.monotonic()
        for idx, arq in enumerate(arquivos, start=1):
            if idx % 25 == 0:
                logger.info("Progresso: %d/%d", idx, len(arquivos))
            status, cls_nome = _ingerir_um(arq, grafo)
            por_status[status] += 1
            if cls_nome:
                por_extrator_usado[cls_nome] += 1

        stats_pos = _rodar_fases_pos_ingestao(grafo)

        snap_depois = _contagem_grafo(grafo)
        duracao = time.monotonic() - inicio
        _imprimir_sumario_execucao(
            arquivos, por_status, por_extrator_usado, duracao,
            snap_antes, snap_depois, stats_pos,
        )
    finally:
        grafo.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Não importa quão lentamente vocês andem, o importante é que não parem." -- Confúcio
