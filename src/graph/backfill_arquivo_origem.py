"""Sprint 98a: backfill de metadata.arquivo_origem em nodes documento com
path quebrado (apontando para arquivos que foram renomeados/movidos).

Distinto de `backfill_arquivo_original.py` (Sprint 87.5):
  - 87.5 preenche `arquivo_original` (com L) quando vazio.
  - 98a corrige `arquivo_origem` (sem L) quando aponta para Path inexistente.

Causa raiz: Sprint 98 (commit a48b843) renomeou 24 holerites no filesystem
de `holerite_<timestamp>.pdf` para `HOLERITE_<YYYY-MM>_<empresa>_<liquido>.pdf`,
mas o `metadata.arquivo_origem` no node ficou apontando para o nome antigo.

Heurísticas (em ordem):
  1. Holerite: usa `mes_ref` + `razao_social` para procurar
     `HOLERITE_<mes>_<empresa>_*.pdf` em `data/raw/<pessoa>/holerites/`.
  2. DAS PARCSN: usa `mes_ref` + `total` para procurar
     `DAS_PARCSN_<YYYY-MM-DD>_*.pdf` em `data/raw/<pessoa>/impostos/das_parcsn/`.
  3. Genérico: procura por `tipo_documento` + `mes_ref` em qualquer pasta
     `data/raw/<pessoa>/`.

Idempotente: rodar 2x devolve o mesmo resultado (paths já corrigidos passam
o teste `Path.exists()` e são skipped).

Uso programático:
    from src.graph.backfill_arquivo_origem import backfill_arquivo_origem
    rel = backfill_arquivo_origem(grafo, dry_run=False)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.graph.db import GrafoDB
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.backfill_arquivo_origem")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_RAIZ_RAW_PADRAO: Path = _RAIZ_REPO / "data" / "raw"


def _resolver_holerite(meta: dict[str, Any], raiz_raw: Path) -> Path | None:
    """Heurística: HOLERITE_<mes>_<empresa>_*.pdf em data/raw/<pessoa>/holerites/."""
    mes = (meta.get("periodo_apuracao") or "").strip()
    razao = (meta.get("razao_social") or "").upper().strip()
    if not mes or not razao:
        return None

    # Empresa derivada da razao_social.
    if "G4F" in razao:
        empresa = "G4F"
    elif "INFOBASE" in razao:
        empresa = "INFOBASE"
    else:
        return None

    # Procura em data/raw/<pessoa>/holerites/
    for pessoa_dir in raiz_raw.iterdir():
        if not pessoa_dir.is_dir():
            continue
        holerites_dir = pessoa_dir / "holerites"
        if not holerites_dir.is_dir():
            continue
        # Padrão: HOLERITE_2025-12_G4F_*.pdf
        candidatos = sorted(holerites_dir.glob(f"HOLERITE_{mes}_{empresa}_*.pdf"))
        if len(candidatos) == 1:
            return candidatos[0]
        if len(candidatos) > 1:
            # Múltiplos: tenta desempate por valor líquido no metadata.
            liquido = meta.get("liquido")
            if liquido:
                liquido_int = int(round(float(liquido)))
                # Nome usa o liquido integer (sem decimais).
                for cand in candidatos:
                    nome = cand.stem  # ex: HOLERITE_2025-10_G4F_2164
                    partes = nome.split("_")
                    if len(partes) >= 4 and partes[-1] == str(liquido_int):
                        return cand
            # Fallback: primeiro lexicograficamente.
            return candidatos[0]
    return None


def _resolver_das_parcsn(meta: dict[str, Any], raiz_raw: Path) -> Path | None:
    """Heurística: DAS_PARCSN_<YYYY-MM-DD>_*.pdf em impostos/das_parcsn/."""
    venc = meta.get("vencimento") or meta.get("data_emissao")
    if not venc:
        return None
    venc_str = str(venc)[:10]  # YYYY-MM-DD
    for pessoa_dir in raiz_raw.iterdir():
        if not pessoa_dir.is_dir():
            continue
        das_dir = pessoa_dir / "impostos" / "das_parcsn"
        if not das_dir.is_dir():
            continue
        candidatos = sorted(das_dir.glob(f"DAS_PARCSN_{venc_str}_*.pdf"))
        if candidatos:
            return candidatos[0]
    return None


def _resolver_generico(meta: dict[str, Any], raiz_raw: Path) -> Path | None:
    """Fallback: procura por nome exato em raiz_raw.

    P1-04 fix Sprint 108: usa rglob com nome literal (sem prefixo glob `*`)
    para evitar match em pastas erradas (ex: arquivo da Vitória casando
    sufixo de outro arquivo do Andre). glob.escape protege caracteres
    especiais no nome.
    """
    import glob as _glob

    arquivo_origem_antigo = meta.get("arquivo_origem")
    if not arquivo_origem_antigo:
        return None
    nome_antigo = Path(arquivo_origem_antigo).name
    if not nome_antigo:
        return None
    # rglob por nome exato (escapado) para evitar substring match cross-pasta.
    for arq in raiz_raw.rglob(_glob.escape(nome_antigo)):
        if arq.is_file():
            return arq
    return None


def detectar_paths_quebrados(grafo: GrafoDB) -> list[dict[str, Any]]:
    """Lista nodes documento cujo `metadata.arquivo_origem` aponta para
    arquivo inexistente.

    Retorna lista de dicts com {id, nome_canonico, metadata, arquivo_origem_antigo}.
    """
    cur = grafo._conn.execute(  # noqa: SLF001
        "SELECT id, tipo, nome_canonico, metadata, aliases FROM node WHERE tipo='documento'"
    )
    quebrados: list[dict[str, Any]] = []
    for row in cur:
        meta = json.loads(row[3] or "{}")
        ao = meta.get("arquivo_origem")
        if ao and not Path(ao).exists():
            quebrados.append(
                {
                    "id": row[0],
                    "nome_canonico": row[2],
                    "aliases": json.loads(row[4] or "[]"),
                    "metadata": meta,
                    "arquivo_origem_antigo": ao,
                }
            )
    return quebrados


def resolver_via_metadata(meta: dict[str, Any], raiz_raw: Path) -> Path | None:
    """Aplica heurísticas em ordem para achar o arquivo atual via metadata."""
    tipo = meta.get("tipo_documento", "")
    if tipo == "holerite":
        achado = _resolver_holerite(meta, raiz_raw)
        if achado:
            return achado
    if tipo.startswith("das_parcsn"):
        achado = _resolver_das_parcsn(meta, raiz_raw)
        if achado:
            return achado
    return _resolver_generico(meta, raiz_raw)


def backfill_arquivo_origem(
    grafo: GrafoDB,
    raiz_raw: Path | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Detecta e corrige `metadata.arquivo_origem` em nodes com path quebrado.

    Retorna dict com:
      - quebrados: int (total detectados)
      - resolvidos: int (achados por heurística)
      - persistidos: int (escritos no grafo; igual a resolvidos quando não-dry)
      - nao_resolvidos: int
      - sem_estrategia: list[dict] (nodes onde nenhuma heurística funcionou)
    """
    raiz = raiz_raw if raiz_raw is not None else _RAIZ_RAW_PADRAO

    quebrados = detectar_paths_quebrados(grafo)
    stats: dict[str, Any] = {
        "quebrados": len(quebrados),
        "resolvidos": 0,
        "persistidos": 0,
        "nao_resolvidos": 0,
        "sem_estrategia": [],
    }

    for q in quebrados:
        meta = q["metadata"]
        achado = resolver_via_metadata(meta, raiz)
        if achado is None:
            stats["nao_resolvidos"] += 1
            stats["sem_estrategia"].append(
                {
                    "id": q["id"],
                    "nome": q["nome_canonico"][:50],
                    "arquivo_antigo": Path(q["arquivo_origem_antigo"]).name,
                }
            )
            logger.warning(
                "node id=%s sem estratégia: tipo=%s mes=%s",
                q["id"],
                meta.get("tipo_documento"),
                meta.get("periodo_apuracao"),
            )
            continue
        stats["resolvidos"] += 1
        if not dry_run:
            meta_novo = dict(meta)
            meta_novo["arquivo_origem"] = str(achado.resolve())
            # Reflete também em arquivo_original para compat com sync_rico.
            if not meta_novo.get("arquivo_original"):
                meta_novo["arquivo_original"] = str(achado.resolve())
            grafo.upsert_node(
                tipo="documento",
                nome_canonico=q["nome_canonico"],
                metadata=meta_novo,
                aliases=q["aliases"],
            )
            stats["persistidos"] += 1
            logger.info(
                "node id=%s atualizado: %s -> %s",
                q["id"],
                Path(q["arquivo_origem_antigo"]).name,
                achado.name,
            )
        else:
            logger.info(
                "[dry-run] node id=%s seria atualizado: %s -> %s",
                q["id"],
                Path(q["arquivo_origem_antigo"]).name,
                achado.name,
            )

    return stats


# "O caminho que muda exige novo mapa." -- princípio do path vivo
