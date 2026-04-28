"""Sprint 103 -- Fase Opus: extrai transcricao crua de cada pendencia do Revisor.

Para cada pendencia retornada por `listar_pendencias_revisao`:
  1. Tenta extrair texto via pdfplumber (PDFs nativos).
  2. Fallback para OCR via tesseract (PDFs scaneados / imagens).
  3. Captura metadata do grafo / classifier para comparacao.
  4. Salva em data/output/transcricoes_opus/transcricoes.json.

O JSON serve como insumo para o supervisor (modelo IA) ler cada
transcricao + metadata ETL e decidir o valor_opus de cada dimensao
(data, valor, itens, fornecedor, pessoa). As decisoes do Opus são
persistidas em data/output/revisao_humana.sqlite via salvar_marcacao(...,
valor_opus=...).
"""

from __future__ import annotations

import json
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

_DESTINO = _RAIZ / "data" / "output" / "transcricoes_opus" / "transcricoes.json"


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


def main() -> int:
    pendencias = listar_pendencias_revisao()
    print(f"Total pendencias: {len(pendencias)}", file=sys.stderr)

    saida: list[dict] = []
    for i, p in enumerate(pendencias, start=1):
        item_id = p["item_id"]
        caminho_str = p.get("caminho") or ""
        tipo = p["tipo"]
        meta = p.get("metadata") or {}

        print(f"[{i}/{len(pendencias)}] {tipo} :: {item_id[-60:]}", file=sys.stderr)

        # Extrai texto cru (ou listagem de diretorio)
        if caminho_str and Path(caminho_str).exists():
            if Path(caminho_str).is_dir():
                texto = _diretorio_pendencia(p)
            else:
                texto = _extrair_texto(Path(caminho_str))
        else:
            texto = "[arquivo não acessivel ou caminho vazio]"

        # Trunca transcricoes muito longas (> 8KB) para não explodir o JSON
        if len(texto) > 8000:
            texto = texto[:8000] + "\n\n[...transcricao truncada após 8000 chars...]"

        # Calcula valor_etl para cada dimensao canonica
        valores_etl: dict[str, str] = {}
        for dim in ("data", "valor", "itens", "fornecedor", "pessoa"):
            valores_etl[dim] = extrair_valor_etl_para_dimensao(p, dim)

        saida.append(
            {
                "indice": i,
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
        )

    _DESTINO.parent.mkdir(parents=True, exist_ok=True)
    _DESTINO.write_text(
        json.dumps(saida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nGravado em {_DESTINO}", file=sys.stderr)
    print(f"Total: {len(saida)} pendencias com transcricao + metadata ETL", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
