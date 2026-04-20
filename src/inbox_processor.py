"""Processador de inbox: ponto de entrada do CLI `./run.sh --inbox`.

Sprint 41 (intake universal) consolidou a lógica de detecção/roteamento
em `src.intake.orchestrator.processar_arquivo_inbox`. Este módulo agora
é um WRAPPER FINO que:

  1. Varre `inbox/` por arquivos elegíveis (extensões suportadas).
  2. Para cada um, delega ao orquestrador da Sprint 41.
  3. Decide se descarta o original da inbox (sucesso total -> sim).
  4. Adapta o `RelatorioRoteamento` (rico, da Sprint 41) para o
     `list[dict]` legado consumido por callers/CLI/relatórios.

O contrato externo é PRESERVADO: callers que iteram sobre `processar_inbox`
e olham `r["status"]` continuam funcionando.

Ganhos pós-integração:
  - PDF compilado heterogêneo (cupom + NFC-e no mesmo arquivo) é
    page-splittado e cada página vira um dict no resultado.
  - ZIP/EML são expandidos automaticamente; cada anexo vira um dict.
  - Pessoa é auto-detectada via CPF (Sprint 41b) -- não precisa mais
    organizar manualmente em subpastas pessoa/.
  - Imagens (JPG/PNG/HEIC) entram via OCR (Sprint 41 preview).
  - XML NFe é reconhecido por conteúdo.
  - 15 tipos canônicos no YAML + detector legado bancário cobrem 85%+
    do data/raw/ histórico (validado em prova de fogo Sprint 41c).

Status do dict no resultado:
  - "processado":       artefato roteado para pasta canônica
  - "nao_identificado": artefato em `data/raw/_classificar/` (fallback)
  - "duplicata":        intake é idempotente por sha8 (arquivar_original
                        re-encontra cópia anterior); contado quando o
                        arquivo da inbox tinha cópia previamente arquivada
  - "erro":             exceção catastrófica
"""

from __future__ import annotations

from pathlib import Path

from src.intake.orchestrator import processar_arquivo_inbox
from src.intake.router import ArtefatoArquivado, RelatorioRoteamento, descartar_da_inbox
from src.utils.logger import configurar_logger

logger = configurar_logger("inbox_processor")

RAIZ_PROJETO = Path(__file__).parent.parent

EXTENSOES_SUPORTADAS: set[str] = {
    # Bancário (Sprint 41c -- registry delega ao file_detector legado)
    ".csv",
    ".xlsx",
    ".xls",
    ".ofx",
    # Documental (Sprint 41 -- classifier YAML)
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


# ============================================================================
# Adapter RelatorioRoteamento (rico) -> list[dict] (contrato legado)
# ============================================================================


def _artefato_para_dict(arquivo_origem: Path, artefato: ArtefatoArquivado) -> dict:
    """Converte ArtefatoArquivado em dict no shape esperado pelo legado.

    Status mapping:
      - sucesso=True   -> "processado"
      - sucesso=False  -> "nao_identificado" (fallback _classificar/)

    deteccao:
      - tipo, prioridade, extrator_modulo, origem_sprint, data_detectada_iso
      - banco/pessoa/subtipo derivados do tipo quando bancário
    """
    decisao = artefato.decisao
    status = "processado" if artefato.sucesso else "nao_identificado"
    return {
        "arquivo_original": str(arquivo_origem),
        "destino": str(artefato.caminho_final),
        "deteccao": {
            "tipo": decisao.tipo,
            "prioridade": decisao.prioridade,
            "match_mode": decisao.match_mode,
            "extrator_modulo": decisao.extrator_modulo,
            "origem_sprint": decisao.origem_sprint,
            "data_detectada_iso": decisao.data_detectada_iso,
            "motivo_fallback": decisao.motivo_fallback,
        },
        "status": status,
    }


def _relatorio_para_dicts(arquivo_origem: Path, relatorio: RelatorioRoteamento) -> list[dict]:
    """Expande RelatorioRoteamento em N dicts (1 por artefato).

    Em PDF homogêneo / single envelope, devolve 1 dict.
    Em PDF heterogêneo, ZIP, EML, devolve N dicts.
    Em sucesso parcial, mistura "processado" e "nao_identificado".
    """
    if not relatorio.artefatos:
        return [
            {
                "arquivo_original": str(arquivo_origem),
                "destino": None,
                "deteccao": None,
                "status": "erro",
            }
        ]
    return [_artefato_para_dict(arquivo_origem, art) for art in relatorio.artefatos]


# ============================================================================
# API pública (contrato preservado da versão pré-Sprint 41)
# ============================================================================


def processar_arquivo(
    caminho: Path,
    diretorio_raw: Path | None = None,
    diretorio_nao_identificados: Path | None = None,
) -> list[dict]:
    """Processa UM arquivo da inbox via intake universal (Sprint 41/b/c/d).

    Devolve `list[dict]` -- 1 elemento por ARTEFATO produzido (1 para single,
    N para PDF heterogêneo / ZIP / EML).

    Os parâmetros `diretorio_raw` e `diretorio_nao_identificados` são
    mantidos para compatibilidade de assinatura, mas ignorados: o
    intake universal usa caminhos canônicos (`data/raw/{pessoa}/...` e
    `data/raw/_classificar/`).
    """
    del diretorio_raw, diretorio_nao_identificados  # honra contrato sem usar

    try:
        relatorio = processar_arquivo_inbox(caminho, pessoa="_indefinida")
    except FileNotFoundError:
        logger.warning("arquivo da inbox sumiu antes do processamento: %s", caminho)
        return [
            {
                "arquivo_original": str(caminho),
                "destino": None,
                "deteccao": None,
                "status": "erro",
            }
        ]
    except Exception as exc:  # noqa: BLE001 -- defensivo, pipeline não pode parar
        logger.error("erro inesperado ao processar %s: %s", caminho.name, exc)
        return [
            {
                "arquivo_original": str(caminho),
                "destino": None,
                "deteccao": None,
                "status": "erro",
            }
        ]

    # Sucesso total -> remove original da inbox; senão preserva pra supervisor
    descartar_da_inbox(caminho, relatorio.sucesso_total)

    return _relatorio_para_dicts(caminho, relatorio)


def processar_inbox(diretorio_inbox: Path, diretorio_raw: Path | None = None) -> list[dict]:
    """Processa todos os arquivos da inbox via intake universal.

    Para cada arquivo, expande em N dicts (1 por artefato). Acumula tudo
    numa lista achatada para preservar o contrato legado.

    Args:
        diretorio_inbox: Diretório de entrada (geralmente `inbox/`).
        diretorio_raw:   IGNORADO -- intake usa caminhos canônicos. Mantido
                         para compatibilidade de assinatura.

    Returns:
        Lista achatada de dicts: cada elemento corresponde a UM artefato
        (página de PDF, anexo de ZIP, etc.) com status, destino, detecção.
    """
    del diretorio_raw  # honra contrato sem usar

    if not diretorio_inbox.exists():
        logger.warning("diretório inbox não encontrado: %s", diretorio_inbox)
        return []

    arquivos = [
        f
        for f in sorted(diretorio_inbox.iterdir())
        if f.is_file() and f.suffix.lower() in EXTENSOES_SUPORTADAS
    ]

    if not arquivos:
        logger.info("nenhum arquivo para processar em %s", diretorio_inbox)
        return []

    logger.info("processando %d arquivo(s) do inbox via intake universal", len(arquivos))

    resultados: list[dict] = []
    contadores = {"processado": 0, "duplicata": 0, "nao_identificado": 0, "erro": 0}

    for arquivo in arquivos:
        dicts = processar_arquivo(arquivo)
        resultados.extend(dicts)
        for d in dicts:
            contadores[d["status"]] = contadores.get(d["status"], 0) + 1

    logger.info(
        "intake finalizado: %d artefato(s) -- %d processado, %d nao_identificado, %d erro",
        len(resultados),
        contadores["processado"],
        contadores["nao_identificado"],
        contadores["erro"],
    )

    return resultados


def main() -> None:
    """Ponto de entrada para execução via `python -m src.inbox_processor`."""
    diretorio_inbox = RAIZ_PROJETO / "inbox"

    logger.info("iniciando intake universal: %s", diretorio_inbox)

    resultados = processar_inbox(diretorio_inbox)

    if not resultados:
        logger.info("nenhum arquivo processado")
        return

    for r in resultados:
        status = r["status"].upper()
        origem = Path(r["arquivo_original"]).name
        destino = r["destino"] or "N/A"
        logger.info("[%s] %s -> %s", status, origem, destino)


if __name__ == "__main__":
    main()


# "A liberdade é o reconhecimento da necessidade." -- Baruch Spinoza
