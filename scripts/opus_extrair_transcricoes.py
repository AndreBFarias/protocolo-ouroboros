"""Sprint 103 -- Fase Opus: extrai transcricao crua de cada pendencia do Revisor.

Modos:
  - default: itera `listar_pendencias_revisao()` (27 pendências). Saída em
    `data/output/transcricoes_opus/transcricoes.json` (compat Sprint 103).
  - --estender: amostragem ampliada para a auditoria 4-way (sessão pós-Sprint
    108). Lê o JSON legacy como base, depois escaneia `data/raw/**` por
    PDFs/imagens NÃO visitados, gera transcricao para os novos. Saída em
    `data/output/transcricoes_opus/transcricoes_v2.json`. Usa `--limit N`
    (default 30) para limitar arquivos novos por execução; metadata_etl
    é puxada do grafo quando existe node documento via `arquivo_origem`,
    senão ficam strings vazias por dimensão (sinal claro pro Opus).

Para cada pendencia/arquivo:
  1. Tenta extrair texto via pdfplumber (PDFs nativos).
  2. Fallback para OCR via tesseract (PDFs scaneados / imagens).
  3. Captura metadata do grafo / classifier para comparacao.
  4. Salva no JSON de saída.

O JSON serve como insumo para o supervisor (modelo IA) ler cada
transcricao + metadata ETL e decidir o valor_opus de cada dimensao
(data, valor, itens, fornecedor, pessoa). As decisoes do Opus são
persistidas em data/output/revisao_humana.sqlite via salvar_marcacao(...,
valor_opus=...).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.dashboard.dados_revisor import listar_pendencias_revisao  # noqa: E402
from src.dashboard.paginas.revisor import (  # noqa: E402
    extrair_valor_etl_para_dimensao,
    mascarar_pii,
)
from src.graph.path_canonico import to_relativo  # noqa: E402

_DESTINO_LEGACY = _RAIZ / "data" / "output" / "transcricoes_opus" / "transcricoes.json"
_DESTINO_V2 = _RAIZ / "data" / "output" / "transcricoes_opus" / "transcricoes_v2.json"
_GRAFO_DB = _RAIZ / "data" / "output" / "grafo.sqlite"

# Extensões consideradas pelo modo --estender. Mantém alinhado com extratores
# documentais ativos (PDF, fotos JPG/PNG/HEIC/WEBP).
_EXTENSOES_VISITAVEIS: tuple[str, ...] = (
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
)

# Pastas dentro de data/raw/ que NÃO devem entrar no escaneamento amplo:
# csv/xls/xlsx bancários ja são processados por extractor automatizado e não
# fazem sentido pro fluxo Opus de catalogação documental visual.
_PASTAS_BANCARIAS_PULAR: frozenset[str] = frozenset(
    {
        "itau_cc",
        "santander_cartao",
        "santander_cc",
        "c6_cc",
        "c6_cartao",
        "nubank_cc",
        "nubank_cartao",
        "nubank_pf_cc",
        "nubank_pj_cc",
    }
)


def _ler_pdf_pdfplumber(caminho: Path, max_paginas: int = 5) -> str:
    """Tenta extrair texto via pdfplumber. Devolve string vazia em falha."""
    try:
        import pdfplumber
    except ImportError:
        return ""
    try:
        with pdfplumber.open(caminho) as pdf:
            pedacos: list[str] = []
            for i, pagina in enumerate(pdf.pages[:max_paginas]):
                t = pagina.extract_text() or ""
                if t.strip():
                    pedacos.append(f"=== pagina {i + 1} ===\n{t}")
            return "\n\n".join(pedacos)
    except Exception as e:  # noqa: BLE001
        return f"[pdfplumber erro: {e}]"


def _ocr_via_tesseract(caminho: Path) -> str:
    """Roda tesseract em PDF (rasterizado via pdfplumber image) ou imagem."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "[pytesseract/PIL não instalado]"

    if caminho.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        try:
            img = Image.open(caminho)
            return pytesseract.image_to_string(img, lang="por") or ""
        except Exception as e:  # noqa: BLE001
            return f"[ocr imagem erro: {e}]"

    if caminho.suffix.lower() == ".pdf":
        # Rasteriza primeira pagina via pypdfium2 + tesseract.
        try:
            import pypdfium2 as pdfium  # type: ignore
        except ImportError:
            return "[pypdfium2 não instalado para OCR de PDF]"
        try:
            pdf = pdfium.PdfDocument(str(caminho))
            pedacos: list[str] = []
            for i in range(min(3, len(pdf))):
                page = pdf[i]
                pil = page.render(scale=2).to_pil()
                texto = pytesseract.image_to_string(pil, lang="por") or ""
                if texto.strip():
                    pedacos.append(f"=== pagina {i + 1} (OCR) ===\n{texto}")
            return "\n\n".join(pedacos) or "[OCR rodou mas extraiu 0 chars]"
        except Exception as e:  # noqa: BLE001
            return f"[ocr pdf erro: {e}]"

    return f"[extensao não suportada: {caminho.suffix}]"


def _extrair_texto(caminho: Path) -> str:
    """Estrategia em camadas: pdfplumber primeiro, OCR como fallback.

    Para imagens, vai direto ao OCR. Texto e mascarado para PII antes de
    salvar (LGPD-safe -- transcricoes ficam em disco).
    """
    if not caminho.exists():
        return f"[arquivo não existe: {caminho}]"

    sufixo = caminho.suffix.lower()
    if sufixo == ".pdf":
        nativo = _ler_pdf_pdfplumber(caminho)
        if nativo and len(nativo) > 50:
            return mascarar_pii(nativo)
        # Fallback OCR
        ocr = _ocr_via_tesseract(caminho)
        return mascarar_pii(ocr)
    if sufixo in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"):
        return mascarar_pii(_ocr_via_tesseract(caminho))
    # Outros (txt, csv, xml): le bruto, trunca.
    try:
        bruto = caminho.read_text(encoding="utf-8", errors="replace")
        return mascarar_pii(bruto[:5000])
    except Exception as e:  # noqa: BLE001
        return f"[erro lendo {sufixo}: {e}]"


def _diretorio_pendencia(pendencia: dict) -> str:
    """Para raw_conferir que é diretório, lista arquivos dentro."""
    caminho = pendencia.get("caminho") or ""
    p = Path(caminho)
    if not p.exists() or not p.is_dir():
        return ""
    arquivos = sorted([f.name for f in p.iterdir() if f.is_file()])
    return "Diretório contém: " + ", ".join(arquivos[:20])


def _construir_entry(indice: int, pendencia: dict) -> dict:
    """Monta uma entry do JSON de saída a partir de pendência (real ou sintética).

    PII mascarada defensivamente em todos os campos que recebem texto livre.
    `transcricao` é truncada em 8KB.
    """
    item_id = pendencia["item_id"]
    caminho_str = pendencia.get("caminho") or ""
    tipo = pendencia["tipo"]
    meta = pendencia.get("metadata") or {}

    if caminho_str and Path(caminho_str).exists():
        if Path(caminho_str).is_dir():
            texto = _diretorio_pendencia(pendencia)
        else:
            texto = _extrair_texto(Path(caminho_str))
    else:
        texto = "[arquivo não acessivel ou caminho vazio]"

    if len(texto) > 8000:
        texto = texto[:8000] + "\n\n[...transcricao truncada após 8000 chars...]"

    valores_etl: dict[str, str] = {}
    for dim in ("data", "valor", "itens", "fornecedor", "pessoa"):
        valores_etl[dim] = extrair_valor_etl_para_dimensao(pendencia, dim)

    return {
        "indice": indice,
        "item_id": item_id,
        "tipo": tipo,
        "caminho": caminho_str,
        "metadata_etl": {
            k: mascarar_pii(str(v)) if isinstance(v, str) else v
            for k, v in meta.items()
            if k != "itens"  # itens lista pode estourar
        },
        "valores_etl_por_dimensao": valores_etl,
        "transcricao": texto,
    }


def _buscar_metadata_grafo(arquivo_relativo: str) -> dict:
    """Busca metadata do node documento via `arquivo_origem` (path relativo).

    Retorna dict vazio se arquivo não está no grafo (caso comum em
    --estender: arquivos não-pendentes muitas vezes nem estão catalogados
    ainda). Usa o índice criado pela Sprint AUDIT-INDEX-JSON.
    Falha-soft: erro de SQL retorna `{}` (não aborta o run).
    """
    if not _GRAFO_DB.exists():
        return {}
    try:
        conn = sqlite3.connect(_GRAFO_DB)
        try:
            cur = conn.execute(
                "SELECT metadata FROM node WHERE tipo='documento' "
                "AND json_extract(metadata, '$.arquivo_origem') = ? LIMIT 1",
                (arquivo_relativo,),
            )
            row = cur.fetchone()
            if row is None:
                return {}
            return json.loads(row[0]) if row[0] else {}
        finally:
            conn.close()
    except (sqlite3.Error, json.JSONDecodeError):
        return {}


def _escanear_data_raw(visitados: set[str]) -> list[dict]:
    """Escaneia `data/raw/` por arquivos visitáveis NÃO presentes em `visitados`.

    `visitados` é o set de paths absolutos (string) já presentes no JSON
    legacy/anterior. Retorna pendências sintéticas no formato esperado por
    `_construir_entry`. Pula pastas bancárias (CSV/XLS já têm extrator
    automatizado, não precisam de OCR).
    """
    raiz = _RAIZ / "data" / "raw"
    if not raiz.exists():
        return []
    pendencias: list[dict] = []
    for arquivo in sorted(raiz.rglob("*")):
        if not arquivo.is_file():
            continue
        if arquivo.suffix.lower() not in _EXTENSOES_VISITAVEIS:
            continue
        # Pular extratos bancários (extensão pode ser PDF mas pasta é bancária).
        partes_relativas = arquivo.relative_to(raiz).parts
        if any(parte in _PASTAS_BANCARIAS_PULAR for parte in partes_relativas):
            continue
        caminho_abs = str(arquivo.resolve())
        if caminho_abs in visitados:
            continue
        # Resolve metadata via grafo (fallback: dict vazio).
        rel = to_relativo(arquivo)
        meta = _buscar_metadata_grafo(rel)
        item_id = f"raw/{arquivo.relative_to(raiz)}"
        pendencias.append(
            {
                "item_id": item_id,
                "caminho": caminho_abs,
                "tipo": "estendido_v2",
                "metadata": meta,
            }
        )
    return pendencias


def _carregar_legacy(destino: Path) -> tuple[list[dict], set[str]]:
    """Lê JSON existente para preservar entradas (idempotência do --estender).

    Retorna (lista_entries, set_caminhos_ja_visitados). Set vazio se arquivo
    não existe ou está corrompido.
    """
    if not destino.exists():
        return [], set()
    try:
        bruto = json.loads(destino.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], set()
    if not isinstance(bruto, list):
        return [], set()
    visitados = {entry.get("caminho") for entry in bruto if entry.get("caminho")}
    return bruto, visitados


def _modo_legacy(destino: Path) -> int:
    """Comportamento original Sprint 103: itera apenas pendências do Revisor."""
    pendencias = listar_pendencias_revisao()
    print(f"Total pendencias: {len(pendencias)}", file=sys.stderr)
    saida: list[dict] = []
    for i, p in enumerate(pendencias, start=1):
        print(
            f"[{i}/{len(pendencias)}] {p['tipo']} :: {p['item_id'][-60:]}",
            file=sys.stderr,
        )
        saida.append(_construir_entry(i, p))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(saida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nGravado em {destino}", file=sys.stderr)
    print(f"Total: {len(saida)} pendencias com transcricao + metadata ETL", file=sys.stderr)
    return 0


def _modo_estender(destino: Path, limit: int) -> int:
    """Modo amplo: lê transcricoes legacy + adiciona até `limit` arquivos novos.

    Estratégia idempotente: se arquivo já está no JSON destino (pelo path
    absoluto), pula. Permite rodar várias vezes sem inflar resultado.

    Inclui também as pendências do Revisor que ainda não estão no destino —
    garante que as 27 originais venham junto na primeira execução.
    """
    legacy, visitados = _carregar_legacy(destino)
    print(f"[estender] {len(legacy)} entradas existentes em {destino.name}", file=sys.stderr)

    # Fase A: pendências do Revisor não-visitadas (27 da Sprint 103 + futuras).
    pendencias = listar_pendencias_revisao()
    novas_pendencias_revisor = [
        p for p in pendencias if (p.get("caminho") or "") not in visitados
    ]
    print(
        f"[estender] {len(novas_pendencias_revisor)} pendências Revisor novas",
        file=sys.stderr,
    )

    # Fase B: arquivos data/raw fora das pendências.
    visitados_a_partir_de_pendencias = visitados | {
        p.get("caminho") for p in novas_pendencias_revisor if p.get("caminho")
    }
    arquivos_novos = _escanear_data_raw(visitados_a_partir_de_pendencias)
    print(
        f"[estender] {len(arquivos_novos)} arquivos data/raw não-visitados encontrados",
        file=sys.stderr,
    )

    # Aplica limit ao TOTAL de novos (pendências + escaneados).
    a_processar: list[dict] = list(novas_pendencias_revisor) + list(arquivos_novos)
    if limit > 0 and len(a_processar) > limit:
        a_processar = a_processar[:limit]
        print(f"[estender] limitado a {limit} novos por execução", file=sys.stderr)

    saida = list(legacy)
    proximo_indice = max((e.get("indice", 0) for e in saida), default=0) + 1
    for i, p in enumerate(a_processar):
        print(
            f"[estender {i + 1}/{len(a_processar)}] {p['tipo']} :: {p['item_id'][-60:]}",
            file=sys.stderr,
        )
        saida.append(_construir_entry(proximo_indice + i, p))

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(saida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"\nGravado em {destino}\n"
        f"Total: {len(saida)} entries ({len(legacy)} existentes + "
        f"{len(saida) - len(legacy)} novas)",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extrai transcrições crus para a fase Opus do Revisor. Default: "
            "modo legacy (apenas pendências). --estender amplia escaneando "
            "data/raw."
        )
    )
    parser.add_argument(
        "--estender",
        action="store_true",
        help="Modo amplo: escaneia data/raw e merge com JSON existente.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Limite de novos arquivos por execução em --estender (default 30; 0 = sem limite).",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="Caminho do JSON de saída. Default: transcricoes.json (legacy) "
        "ou transcricoes_v2.json (--estender).",
    )
    args = parser.parse_args(argv)

    destino = args.saida or (_DESTINO_V2 if args.estender else _DESTINO_LEGACY)
    if args.estender:
        return _modo_estender(destino, args.limit)
    return _modo_legacy(destino)


if __name__ == "__main__":
    sys.exit(main())
