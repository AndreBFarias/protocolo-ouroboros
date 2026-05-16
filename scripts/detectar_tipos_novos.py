"""Detector de tipos documentais novos em `data/raw/_classificar/`.

Sprint AUTO-TIPO-PROPOSTAS-DASHBOARD (2026-05-16). Varre o diretório de
fósseis não-classificados, agrupa por características (extensão + tokens
recorrentes no nome + texto extraível dos primeiros KB), e propõe entries
para `mappings/tipos_documento.yaml`. Output em
`data/output/propostas_tipo_novo.json`, consumido pela página Streamlit
`src/dashboard/paginas/tipos_pendentes.py`.

Heurísticas (em ordem):

1. **Extensão**: arquivos `.pdf` formam universo distinto de `.jpeg`.
2. **Nome canônico**: tokens (≥4 chars, lowercase) recorrentes no nome
   de ≥2 arquivos viram candidato a id (e.g. `nfse` em `nfse-2024.pdf`).
3. **Conteúdo**: primeiros 500 chars via pdfplumber/PIL (se aplicável)
   fornecem n-grams para regex_conteudo.

Schema do JSON gerado:

```json
{
  "gerado_em": "ISO 8601",
  "total_arquivos_analisados": 7,
  "propostas": [
    {
      "id_proposto": "nfse_servico",
      "n_amostras": 3,
      "exemplos_sha256": ["abc123...", "def456..."],
      "exemplos_paths_relativos": ["data/raw/_classificar/x.pdf", ...],
      "regex_candidatos": ["NFS-e\\\\s+N\\\\u00ba"],
      "mime_principal": "application/pdf",
      "extensao_principal": ".pdf",
      "confianca_global": 0.78
    }
  ],
  "arquivos_sem_grupo": ["data/raw/_classificar/orfao.pdf"]
}
```

Uso CLI:

    python scripts/detectar_tipos_novos.py                  # dry-run
    python scripts/detectar_tipos_novos.py --apply          # grava JSON
    python scripts/detectar_tipos_novos.py --min-amostras 3 # threshold (default 2)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
DIR_CLASSIFICAR = _RAIZ / "data" / "raw" / "_classificar"
PATH_PROPOSTAS = _RAIZ / "data" / "output" / "propostas_tipo_novo.json"

EXTRACAO_BYTES_MAX = 8192  # 8KB suficiente para cabeçalho


def _sha256_arquivo(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _extrair_texto_curto(p: Path) -> str:
    """Extrai até 500 chars do conteúdo textual. Falha silenciosa = ''."""
    ext = p.suffix.lower()
    if ext == ".pdf":
        try:
            import pdfplumber  # type: ignore[import-untyped]

            with pdfplumber.open(p) as pdf:
                if not pdf.pages:
                    return ""
                txt = pdf.pages[0].extract_text() or ""
                return txt[:500]
        except (ImportError, OSError, ValueError):
            return ""
    if ext in (".txt", ".md", ".csv", ".xml", ".html"):
        try:
            return p.read_text(encoding="utf-8", errors="ignore")[:500]
        except OSError:
            return ""
    # Imagens, ofx, xlsx, etc não tentamos OCR aqui (pesado).
    return ""


def _tokens_nome(nome: str) -> list[str]:
    """Tokens >=4 chars em lowercase, ignorando dígitos isolados."""
    raw = re.findall(r"[a-zA-Z]{4,}", nome.lower())
    # Filtra stopwords óbvias:
    stop = {"file", "documento", "pdf", "image", "scan", "photo"}
    return [t for t in raw if t not in stop]


def _tokens_conteudo(texto: str) -> list[str]:
    """Tokens >=4 chars do conteúdo, sem stopwords numéricas."""
    if not texto:
        return []
    raw = re.findall(r"[a-zA-ZÀ-ÿ]{4,}", texto.lower())
    stop = {
        "para",
        "como",
        "este",
        "esta",
        "esse",
        "isso",
        "mais",
        "todos",
        "todas",
    }
    return [t for t in raw if t not in stop]


def _agrupar_arquivos(arquivos: list[Path], min_amostras: int) -> dict[str, list[Path]]:
    """Agrupa arquivos por tokens recorrentes no nome.

    Estratégia: para cada arquivo, gera lista de tokens; para cada par de
    arquivos com ≥1 token em comum, agrupa. Vence o token de maior
    frequência global como id_proposto.

    Devolve dict: {id_proposto: [Paths]}, com cada grupo tendo
    ≥`min_amostras` arquivos.
    """
    if not arquivos:
        return {}

    # Map token -> set de arquivos que o contém:
    token_para_arquivos: dict[str, set[Path]] = {}
    for p in arquivos:
        for t in _tokens_nome(p.name):
            token_para_arquivos.setdefault(t, set()).add(p)

    # Filtra tokens raros (< min_amostras arquivos):
    grupos: dict[str, list[Path]] = {}
    for token, conj in token_para_arquivos.items():
        if len(conj) < min_amostras:
            continue
        grupos[token] = sorted(conj)

    return grupos


def _propor_regex(arquivos: list[Path]) -> list[str]:
    """Propõe regex candidatos para `regex_conteudo` baseado em n-grams comuns."""
    textos = [_extrair_texto_curto(p) for p in arquivos]
    textos = [t for t in textos if t]
    if len(textos) < 2:
        return []
    # Tokens compartilhados por TODOS os textos:
    sets = [set(_tokens_conteudo(t)) for t in textos]
    comuns = set.intersection(*sets) if sets else set()
    if not comuns:
        return []
    # Top 3 tokens mais frequentes globalmente (com escape regex):
    contador = Counter()
    for s in sets:
        contador.update(s)
    top = [t for t, _ in contador.most_common(5) if t in comuns][:3]
    return [re.escape(t) for t in top]


def _confianca_global(arquivos: list[Path], regex_count: int) -> float:
    """Heurística simples de confiança: 0.4 * (n/10) + 0.6 * (regex/3)."""
    n_norm = min(len(arquivos) / 10.0, 1.0)
    regex_norm = min(regex_count / 3.0, 1.0)
    return round(0.4 * n_norm + 0.6 * regex_norm, 2)


def gerar_propostas(min_amostras: int = 2) -> dict:
    """Constrói payload de propostas para JSON.

    Quando `data/raw/_classificar/` não existe ou está vazio, devolve
    estrutura com `propostas: []` (idempotente, não-erro).
    """
    arquivos = []
    if DIR_CLASSIFICAR.exists():
        arquivos = [p for p in DIR_CLASSIFICAR.rglob("*") if p.is_file()]

    grupos = _agrupar_arquivos(arquivos, min_amostras=min_amostras)
    arquivos_agrupados: set[Path] = set()
    propostas = []
    for id_proposto, ps in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
        regex_cand = _propor_regex(ps)
        ext_counter = Counter(p.suffix.lower() for p in ps)
        ext_principal = ext_counter.most_common(1)[0][0] if ext_counter else ""
        mime = {
            ".pdf": "application/pdf",
            ".jpeg": "image/jpeg",
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".xml": "application/xml",
        }.get(ext_principal, "application/octet-stream")

        propostas.append(
            {
                "id_proposto": id_proposto,
                "n_amostras": len(ps),
                "exemplos_sha256": [_sha256_arquivo(p)[:16] for p in ps[:5]],
                "exemplos_paths_relativos": [
                    str(p.relative_to(_RAIZ)) for p in ps[:5]
                ],
                "regex_candidatos": regex_cand,
                "mime_principal": mime,
                "extensao_principal": ext_principal,
                "confianca_global": _confianca_global(ps, len(regex_cand)),
            }
        )
        arquivos_agrupados.update(ps)

    sem_grupo = [
        str(p.relative_to(_RAIZ)) for p in arquivos if p not in arquivos_agrupados
    ]

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "total_arquivos_analisados": len(arquivos),
        "propostas": propostas,
        "arquivos_sem_grupo": sem_grupo,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detector de tipos novos em _classificar/")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava JSON em data/output/propostas_tipo_novo.json (default: dry-run stdout)",
    )
    parser.add_argument(
        "--min-amostras",
        type=int,
        default=2,
        help="Mínimo de arquivos por grupo para virar proposta (default: 2)",
    )
    args = parser.parse_args(argv)

    payload = gerar_propostas(min_amostras=args.min_amostras)

    if not args.apply:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    PATH_PROPOSTAS.parent.mkdir(parents=True, exist_ok=True)
    PATH_PROPOSTAS.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sys.stdout.write(
        f"Propostas em {PATH_PROPOSTAS}\n"
        f"  total analisados: {payload['total_arquivos_analisados']}\n"
        f"  propostas geradas: {len(payload['propostas'])}\n"
        f"  sem grupo: {len(payload['arquivos_sem_grupo'])}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Toda regra começa como observação de padrão repetido." -- princípio do indutor honesto
