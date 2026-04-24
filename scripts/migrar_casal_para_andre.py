"""Migra arquivos identificados como do Andre de data/raw/casal/ para data/raw/andre/.

Origem: Sprint 90 (pessoa_detector por CNPJ + razão social + alias) detecta
corretamente que DAS PARCSN e certidões Receita são do Andre (via CNPJ
45.850.636 ou razão social). Mas os arquivos já processados antes da
Sprint 90 continuam fisicamente em data/raw/casal/. Este script faz a
migração física usando o detector novo.

Uso:
    python scripts/migrar_casal_para_andre.py            # dry-run
    python scripts/migrar_casal_para_andre.py --executar # aplica movimentações

Contratos:
- Preserva data/raw/originais/ (hashes imutáveis, ADR-18).
- Só migra arquivos em data/raw/casal/<categoria>/*.pdf (não recursivo nos
  subdiretórios especiais como _envelopes/).
- Usa o próprio pessoa_detector: se detectar "andre" via pessoas.yaml,
  move; se "vitoria" ou "casal", deixa como está.
- Idempotente por path: se destino já existe, pula com log INFO.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.intake.pessoa_detector import detectar_pessoa  # noqa: E402
from src.intake.preview import gerar_preview  # noqa: E402
from src.utils.logger import configurar_logger  # noqa: E402

logger = configurar_logger("scripts.migrar_casal_para_andre")


def _listar_candidatos(raiz_casal: Path) -> list[Path]:
    """Lista PDFs em data/raw/casal/<categoria>/*.pdf (depth 2-3)."""
    if not raiz_casal.exists():
        return []
    candidatos: list[Path] = []
    for subdir in sorted(raiz_casal.iterdir()):
        if not subdir.is_dir():
            continue
        # Dentro de cada subdir (boletos/, impostos/, documentos/, etc),
        # procura PDFs em até 2 níveis
        for arq in subdir.rglob("*.pdf"):
            if arq.is_file():
                candidatos.append(arq)
    return candidatos


def _detectar_mime(caminho: Path) -> str:
    """Detecta MIME heurístico (pdfplumber só aceita PDF)."""
    return "application/pdf" if caminho.suffix.lower() == ".pdf" else "application/octet-stream"


def _destino_andre(arquivo_casal: Path, raiz_raw: Path) -> Path:
    """Reescreve data/raw/casal/X/Y.pdf -> data/raw/andre/X/Y.pdf."""
    partes = arquivo_casal.relative_to(raiz_raw).parts
    assert partes[0] == "casal", f"esperado casal/ no topo, achei {partes}"
    nova = ("andre",) + partes[1:]
    return raiz_raw.joinpath(*nova)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Aplica as movimentações (default: dry-run)",
    )
    args = parser.parse_args()

    raiz_raw = _RAIZ / "data" / "raw"
    raiz_casal = raiz_raw / "casal"

    candidatos = _listar_candidatos(raiz_casal)
    logger.info("Candidatos em data/raw/casal/: %d arquivos", len(candidatos))

    plano: list[tuple[Path, Path]] = []
    ja_andre = 0
    ficam_casal = 0
    vai_vitoria = 0

    for arquivo in candidatos:
        try:
            preview = gerar_preview(arquivo, _detectar_mime(arquivo))
        except Exception as exc:  # noqa: BLE001
            logger.warning("falha ao gerar preview de %s: %s", arquivo.name, exc)
            preview = None

        pessoa, fonte = detectar_pessoa(arquivo, preview or "")
        if pessoa == "andre":
            destino = _destino_andre(arquivo, raiz_raw)
            plano.append((arquivo, destino))
        elif pessoa == "vitoria":
            vai_vitoria += 1
            logger.info("%s -> vitoria (fonte=%s), migração não-automática", arquivo.name, fonte)
        else:
            ficam_casal += 1

    logger.info(
        "Plano: %d migrar p/ andre, %d ficam casal, %d iriam vitoria",
        len(plano),
        ficam_casal,
        vai_vitoria,
    )

    if not args.executar:
        logger.info("--- DRY-RUN --- use --executar para aplicar")
        for origem, destino in plano[:10]:
            logger.info("  %s -> %s", origem.relative_to(raiz_raw), destino.relative_to(raiz_raw))
        if len(plano) > 10:
            logger.info("  ... e mais %d arquivos", len(plano) - 10)
        return 0

    # Executar
    movidos = 0
    pulados = 0
    for origem, destino in plano:
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            # Já foi migrado antes (idempotência); remove origem para não duplicar
            try:
                origem.unlink()
                logger.info("destino já existe, origem removida: %s", origem.name)
                pulados += 1
            except OSError as exc:
                logger.warning("falha ao remover origem duplicada %s: %s", origem, exc)
            continue
        try:
            shutil.move(str(origem), str(destino))
            movidos += 1
            if movidos <= 5 or movidos % 10 == 0:
                logger.info(
                    "  (%d/%d) %s -> %s", movidos, len(plano), origem.name, destino.parent.name
                )
        except (OSError, shutil.Error) as exc:
            logger.error("falha ao mover %s -> %s: %s", origem, destino, exc)

    logger.info(
        "Resumo: %d movidos, %d pulados, total planejado %d. ja_andre=%d",
        movidos,
        pulados,
        len(plano),
        ja_andre,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# "Classificar tarde e bem é melhor que classificar cedo e errado." -- princípio de migração
