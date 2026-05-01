"""Adapter para coabitação estrutural com o vault Obsidian Controle de Bordo.

Sprint 70 — Fase IOTA P0. Governado por ADR-18.

O dono do repositório usa um vault Obsidian (`~/Controle de Bordo/`) cujo motor próprio em
`.sistema/scripts/` detecta e arquiva notas pessoais. O vault tem uma pasta
`Inbox/` onde ele larga tudo, incluindo arquivos financeiros (PDFs, CSVs,
fotos de cupom). Este módulo:

  1. Varre `$BORDO_DIR/Inbox/` (default `~/Controle de Bordo/Inbox/`) + os
     legados `./inbox/` e `./data/inbox/` (ordem declarada em
     `mappings/inbox_routing.yaml`).
  2. Para cada arquivo, classifica via `src.intake.registry.detectar_tipo`.
  3. Se o tipo está em `tipos_absorvidos` (YAML), preserva cópia em
     `data/raw/originais/{sha256_16}.ext` e delega o processamento ao
     `src.inbox_processor.processar_arquivo` (que move para
     `data/raw/<pessoa>/<banco-ou-tipo>/`).
  4. Se o tipo é desconhecido (não casa nenhuma regra) ou a extensão não é
     suportada (ex.: `.md` de nota pessoal), o arquivo permanece na origem
     para o motor do vault cuidar. Ouroboros nunca toca forbidden zones
     (`.sistema/`, `Trabalho/`, `Segredos/`, `Arquivo/` — ADR-18).

Contrato externo:

    python -m src.integrations.controle_bordo [--dry-run] [--vault PATH]

Imprime relatório estruturado de roteamento por arquivo. Em `--dry-run`
(default) nada é movido.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from src.intake.orchestrator import detectar_mime
from src.intake.preview import gerar_preview
from src.intake.registry import detectar_tipo
from src.utils.logger import configurar_logger

logger = configurar_logger("integrations.controle_bordo")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_CAMINHO_YAML: Path = _RAIZ_REPO / "mappings" / "inbox_routing.yaml"

# Extensões que NUNCA saem do vault (prosa markdown, texto puro de nota).
# Todo o resto é candidato a classificação e eventual roteamento.
_EXTENSOES_NOTA_PESSOAL: frozenset[str] = frozenset({".md", ".markdown"})

# Extensões financeiras reconhecidas (delegadas ao registry).
_EXTENSOES_CANDIDATAS: frozenset[str] = frozenset(
    {
        ".csv",
        ".xlsx",
        ".xls",
        ".ofx",
        ".pdf",
        ".xml",
        ".eml",
        ".zip",
        ".jpg",
        ".jpeg",
        ".png",
        ".heic",
        ".heif",
        ".webp",
        ".txt",
    }
)


# ============================================================================
# Configuração
# ============================================================================


@dataclass(frozen=True)
class ConfigRoteamento:
    """Representa `mappings/inbox_routing.yaml` parseado."""

    sources: tuple[Path, ...]
    tipos_absorvidos: frozenset[str]
    preservar_original: bool
    original_dir: Path
    hash_prefixo_chars: int
    vault_forbidden: frozenset[str]


def vault_root() -> Path:
    """Raiz do vault Controle de Bordo. Resolve `$BORDO_DIR` com fallback."""
    override = os.environ.get("BORDO_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Controle de Bordo"


def _expandir_source(path_bruto: str) -> Path:
    """Expande placeholders e converte para Path absoluto relativo ao repo."""
    expandido = os.path.expandvars(path_bruto)
    if "${BORDO_DIR}" in path_bruto and "BORDO_DIR" not in os.environ:
        # expandvars deixa placeholder não resolvido como literal; resolvemos
        # manualmente via vault_root() quando ${BORDO_DIR} não está setado.
        expandido = expandido.replace("${BORDO_DIR}", str(vault_root()))
    caminho = Path(expandido).expanduser()
    if not caminho.is_absolute():
        caminho = (_RAIZ_REPO / caminho).resolve()
    return caminho


def carregar_config(caminho_yaml: Path | None = None) -> ConfigRoteamento:
    """Lê `mappings/inbox_routing.yaml` e devolve `ConfigRoteamento`."""
    yaml_path = caminho_yaml or _CAMINHO_YAML
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML de roteamento ausente: {yaml_path}")
    dados = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    fontes = tuple(
        _expandir_source(item["path"])
        for item in sorted(
            dados.get("inbox_sources", []),
            key=lambda x: x.get("prioridade", 99),
        )
    )
    tipos = frozenset(dados.get("tipos_absorvidos", []))
    preservar = bool(dados.get("preservar_original", True))
    original_dir_raw = dados.get("original_dir", "data/raw/originais")
    original_dir = (_RAIZ_REPO / original_dir_raw).resolve()
    prefixo = int(dados.get("hash_prefixo_chars", 16))
    forbidden = frozenset(dados.get("vault_forbidden", []))

    return ConfigRoteamento(
        sources=fontes,
        tipos_absorvidos=tipos,
        preservar_original=preservar,
        original_dir=original_dir,
        hash_prefixo_chars=prefixo,
        vault_forbidden=forbidden,
    )


# ============================================================================
# Preservação de original
# ============================================================================


def preservar_original(arquivo: Path, config: ConfigRoteamento) -> Path | None:
    """Copia o arquivo para `data/raw/originais/{sha256_N}.ext`.

    Idempotente: se a cópia já existir (mesmo hash), não sobrescreve. Devolve
    o caminho da cópia, ou None se preservação está desligada no YAML.
    """
    if not config.preservar_original:
        return None

    conteudo = arquivo.read_bytes()
    sha = hashlib.sha256(conteudo).hexdigest()[: config.hash_prefixo_chars]
    destino = config.original_dir / f"{sha}{arquivo.suffix.lower()}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.exists():
        shutil.copy2(arquivo, destino)
        logger.info("original preservado: %s -> %s", arquivo.name, destino.name)
    else:
        logger.debug("original já preservado (hash existente): %s", destino.name)
    return destino


# ============================================================================
# Varredura por source
# ============================================================================


def _listar_candidatos(source: Path, forbidden: frozenset[str]) -> list[Path]:
    """Lista arquivos diretos de `source` (não-recursivo), respeitando forbidden."""
    if not source.exists():
        logger.debug("source inexistente (pulando): %s", source)
        return []
    if not source.is_dir():
        logger.warning("source não é diretório: %s", source)
        return []

    # Varredura não-recursiva: motor do vault gerencia subpastas tipo Pendentes/
    candidatos: list[Path] = []
    for item in sorted(source.iterdir()):
        if not item.is_file():
            continue
        if item.name in forbidden:
            continue
        candidatos.append(item)
    return candidatos


def _eh_forbidden(caminho: Path, config: ConfigRoteamento) -> bool:
    """Verifica se alguma parte do caminho bate com forbidden zones do vault."""
    partes = set(caminho.parts)
    return bool(partes & config.vault_forbidden)


# ============================================================================
# Classificação
# ============================================================================


@dataclass(frozen=True)
class LinhaPlano:
    """Uma entrada no relatório de roteamento."""

    origem: Path
    source: Path
    tipo: str
    acao: str  # "move" | "skip_nota" | "skip_nao_identificado" | "skip_forbidden" | "skip_extensao"
    motivo: str
    destino: Path | None = None
    preservado_em: Path | None = None


def _classificar(arquivo: Path) -> tuple[str, Path | None]:
    """Chama o registry. Devolve `(tipo, pasta_destino_canonica)`.

    Em erro de detecção, devolve ("nao_identificado", None).
    """
    try:
        mime = detectar_mime(arquivo)
        preview = gerar_preview(arquivo, mime) if mime else None
        decisao = detectar_tipo(arquivo, mime, preview, pessoa="_indefinida")
    except Exception as exc:  # noqa: BLE001 -- adapter precisa ser tolerante
        logger.warning("falha ao classificar %s: %s", arquivo.name, exc)
        return ("nao_identificado", None)
    return (decisao.tipo, decisao.pasta_destino)


# ============================================================================
# Roteamento
# ============================================================================


def _planejar_arquivo(
    arquivo: Path,
    source: Path,
    config: ConfigRoteamento,
) -> LinhaPlano:
    """Decide ação para um arquivo sem efetuar movimento algum."""
    if _eh_forbidden(arquivo, config):
        return LinhaPlano(
            origem=arquivo,
            source=source,
            tipo="_forbidden",
            acao="skip_forbidden",
            motivo="caminho inclui forbidden zone do vault (ADR-18)",
        )

    sufixo = arquivo.suffix.lower()
    if sufixo in _EXTENSOES_NOTA_PESSOAL:
        return LinhaPlano(
            origem=arquivo,
            source=source,
            tipo="nota_pessoal",
            acao="skip_nota",
            motivo=f"extensão {sufixo} pertence ao motor do vault",
        )
    if sufixo not in _EXTENSOES_CANDIDATAS:
        return LinhaPlano(
            origem=arquivo,
            source=source,
            tipo="_extensao_nao_suportada",
            acao="skip_extensao",
            motivo=f"extensão {sufixo} não está no conjunto candidato",
        )

    tipo, destino_pasta = _classificar(arquivo)
    if tipo not in config.tipos_absorvidos:
        return LinhaPlano(
            origem=arquivo,
            source=source,
            tipo=tipo,
            acao="skip_nao_identificado",
            motivo="tipo fora de tipos_absorvidos (permanece na origem)",
        )

    return LinhaPlano(
        origem=arquivo,
        source=source,
        tipo=tipo,
        acao="move",
        motivo="tipo financeiro absorvido pelo Ouroboros",
        destino=destino_pasta,
    )


def planejar_roteamento(config: ConfigRoteamento | None = None) -> list[LinhaPlano]:
    """Percorre todas as inbox sources e retorna o plano (sem efeito colateral)."""
    cfg = config or carregar_config()
    plano: list[LinhaPlano] = []
    for source in cfg.sources:
        for arquivo in _listar_candidatos(source, cfg.vault_forbidden):
            plano.append(_planejar_arquivo(arquivo, source, cfg))
    return plano


def executar_roteamento(
    config: ConfigRoteamento | None = None,
    dry_run: bool = True,
) -> list[LinhaPlano]:
    """Planeja e, se `dry_run=False`, aplica efeitos colaterais:

      1. Preserva original em `data/raw/originais/`.
      2. Delega `src.inbox_processor.processar_arquivo` para mover e extrair.

    O adapter NÃO move o arquivo diretamente: confia no pipeline do
    inbox_processor para fazer rename canônico + chamada ao extrator.
    """
    cfg = config or carregar_config()
    plano = planejar_roteamento(cfg)

    if dry_run:
        return plano

    # Import atrasado para evitar ciclo quando adapter é importado só para planejar.
    from src.inbox_processor import processar_arquivo as _processar

    resultado: list[LinhaPlano] = []
    for linha in plano:
        if linha.acao != "move":
            resultado.append(linha)
            continue

        original = preservar_original(linha.origem, cfg)
        try:
            _processar(linha.origem)
        except Exception as exc:  # noqa: BLE001
            logger.error("erro ao processar %s: %s", linha.origem.name, exc)
            resultado.append(linha)
            continue

        resultado.append(
            LinhaPlano(
                origem=linha.origem,
                source=linha.source,
                tipo=linha.tipo,
                acao=linha.acao,
                motivo=linha.motivo,
                destino=linha.destino,
                preservado_em=original,
            )
        )

    return resultado


# ============================================================================
# Relatório
# ============================================================================


def imprimir_relatorio(plano: list[LinhaPlano], *, dry_run: bool) -> None:
    """Imprime tabela textual do plano via logger (stdout + arquivo)."""
    titulo = "DRY-RUN" if dry_run else "EXECUTADO"
    logger.info("=" * 72)
    logger.info("Relatório de roteamento (%s) — %d arquivo(s)", titulo, len(plano))
    logger.info("=" * 72)
    contadores: dict[str, int] = {}
    for linha in plano:
        contadores[linha.acao] = contadores.get(linha.acao, 0) + 1
        destino = linha.destino.name if linha.destino else "-"
        preservado = linha.preservado_em.name if linha.preservado_em else "-"
        logger.info(
            "  [%s] %s (%s) tipo=%s dest=%s orig=%s",
            linha.acao,
            linha.origem.name,
            linha.source.name or linha.source,
            linha.tipo,
            destino,
            preservado,
        )
    logger.info("-" * 72)
    for acao, n in sorted(contadores.items()):
        logger.info("  %-24s %d", acao, n)
    logger.info("=" * 72)


# ============================================================================
# CLI
# ============================================================================


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.integrations.controle_bordo",
        description="Varre vault Controle de Bordo + inbox legado e roteia arquivos financeiros",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Planeja sem aplicar efeitos colaterais (default: True)",
    )
    parser.add_argument(
        "--executar",
        dest="dry_run",
        action="store_false",
        help="Efetiva o plano (move + preserva). Sem esta flag, só imprime.",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=None,
        help="Sobrescreve BORDO_DIR para esta execução (uso em testes)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.vault is not None:
        os.environ["BORDO_DIR"] = str(args.vault)
        logger.info("BORDO_DIR sobrescrito por --vault: %s", args.vault)

    cfg = carregar_config()
    logger.info("sources em ordem: %s", [str(s) for s in cfg.sources])
    logger.info("tipos absorvidos: %d", len(cfg.tipos_absorvidos))

    plano = executar_roteamento(cfg, dry_run=args.dry_run)
    imprimir_relatorio(plano, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Uma porta só, um fluxo só." — princípio operacional, Sprint 70
