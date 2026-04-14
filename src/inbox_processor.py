"""Processador de inbox: detecta, renomeia e move arquivos financeiros automaticamente."""

import shutil
from pathlib import Path
from typing import Optional

from src.utils.file_detector import DeteccaoArquivo, calcular_hash, detectar_arquivo
from src.utils.logger import configurar_logger

logger = configurar_logger("inbox_processor")

RAIZ_PROJETO = Path(__file__).parent.parent

EXTENSOES_SUPORTADAS: set[str] = {".csv", ".xlsx", ".xls", ".pdf"}


def _gerar_nome_padronizado(deteccao: DeteccaoArquivo) -> str:
    """Gera nome de arquivo padronizado a partir da detecção.

    Formato: {banco}_{tipo}_{YYYY-MM}.{ext}
    Para Vitória PJ: {banco}_{subtipo}_{tipo}_{YYYY-MM}.{ext}
    """
    periodo = deteccao.periodo or "sem-data"

    if deteccao.subtipo:
        nome = f"{deteccao.banco}_{deteccao.subtipo}_{deteccao.tipo}_{periodo}"
    else:
        nome = f"{deteccao.banco}_{deteccao.tipo}_{periodo}"

    return f"{nome}.{deteccao.formato}"


def _gerar_diretorio_destino(diretorio_raw: Path, deteccao: DeteccaoArquivo) -> Path:
    """Gera o caminho do diretório destino baseado na detecção.

    Estrutura: data/raw/{pessoa}/{banco}_{subtipo}_{tipo}/
    """
    if deteccao.subtipo:
        subpasta = f"{deteccao.banco}_{deteccao.subtipo}_{deteccao.tipo}"
    else:
        subpasta = f"{deteccao.banco}_{deteccao.tipo}"

    return diretorio_raw / deteccao.pessoa / subpasta


def _verificar_duplicata(caminho_origem: Path, caminho_destino: Path) -> bool:
    """Verifica se o arquivo já existe no destino com mesmo conteúdo (hash)."""
    if not caminho_destino.exists():
        return False

    hash_origem = calcular_hash(caminho_origem)
    hash_destino = calcular_hash(caminho_destino)

    return hash_origem == hash_destino


def processar_arquivo(
    caminho: Path,
    diretorio_raw: Path,
    diretorio_nao_identificados: Path,
) -> dict:
    """Processa um único arquivo do inbox.

    Args:
        caminho: Caminho do arquivo no inbox.
        diretorio_raw: Diretório base para arquivos processados (data/raw/).
        diretorio_nao_identificados: Diretório para arquivos não identificados.

    Returns:
        Dicionário com: arquivo_original, destino, deteccao, status.
    """
    resultado: dict = {
        "arquivo_original": str(caminho),
        "destino": None,
        "deteccao": None,
        "status": "erro",
    }

    deteccao: Optional[DeteccaoArquivo] = detectar_arquivo(caminho)

    if deteccao is None:
        diretorio_nao_identificados.mkdir(parents=True, exist_ok=True)
        destino = diretorio_nao_identificados / caminho.name

        if destino.exists():
            destino = diretorio_nao_identificados / f"{caminho.stem}_dup{caminho.suffix}"

        shutil.move(str(caminho), str(destino))
        resultado["destino"] = str(destino)
        resultado["status"] = "nao_identificado"
        logger.warning(
            "[NAO IDENTIFICADO] %s -> %s",
            caminho.name,
            destino,
        )
        return resultado

    resultado["deteccao"] = {
        "banco": deteccao.banco,
        "tipo": deteccao.tipo,
        "pessoa": deteccao.pessoa,
        "subtipo": deteccao.subtipo,
        "periodo": deteccao.periodo,
        "formato": deteccao.formato,
        "confianca": deteccao.confianca,
    }

    diretorio_destino = _gerar_diretorio_destino(diretorio_raw, deteccao)
    diretorio_destino.mkdir(parents=True, exist_ok=True)

    nome_padronizado = _gerar_nome_padronizado(deteccao)
    caminho_destino = diretorio_destino / nome_padronizado

    if _verificar_duplicata(caminho, caminho_destino):
        caminho.unlink()
        resultado["destino"] = str(caminho_destino)
        resultado["status"] = "duplicata"
        logger.info(
            "[DUPLICATA] %s (já existe em %s)",
            caminho.name,
            caminho_destino,
        )
        return resultado

    if caminho_destino.exists():
        contador = 1
        while caminho_destino.exists():
            if deteccao.subtipo:
                nome_alt = (
                    f"{deteccao.banco}_{deteccao.subtipo}_{deteccao.tipo}_"
                    f"{deteccao.periodo or 'sem-data'}_{contador}.{deteccao.formato}"
                )
            else:
                nome_alt = (
                    f"{deteccao.banco}_{deteccao.tipo}_"
                    f"{deteccao.periodo or 'sem-data'}_{contador}.{deteccao.formato}"
                )
            caminho_destino = diretorio_destino / nome_alt
            contador += 1

    shutil.move(str(caminho), str(caminho_destino))
    resultado["destino"] = str(caminho_destino)
    resultado["status"] = "processado"
    logger.info(
        "[OK] %s -> %s",
        caminho.name,
        caminho_destino,
    )
    return resultado


def processar_inbox(diretorio_inbox: Path, diretorio_raw: Path) -> list[dict]:
    """Processa todos os arquivos do inbox.

    Para cada arquivo:
    1. Chama detectar_arquivo()
    2. Gera nome padronizado: {banco}_{tipo}_{YYYY-MM}.{ext}
    3. Move para data/raw/{pessoa}/{banco}_{subtipo}_{tipo}/
    4. Se arquivo já existe no destino, verifica se é duplicata (hash)
    5. Loga tudo

    Args:
        diretorio_inbox: Diretório de entrada com arquivos brutos.
        diretorio_raw: Diretório base de saída (data/raw/).

    Returns:
        Lista de dicts com: arquivo_original, destino, deteccao, status.
    """
    if not diretorio_inbox.exists():
        logger.warning("Diretório inbox não encontrado: %s", diretorio_inbox)
        return []

    diretorio_nao_identificados = diretorio_inbox / "nao_identificados"

    arquivos = [
        f
        for f in sorted(diretorio_inbox.iterdir())
        if f.is_file() and f.suffix.lower() in EXTENSOES_SUPORTADAS
    ]

    if not arquivos:
        logger.info("Nenhum arquivo para processar em %s", diretorio_inbox)
        return []

    logger.info("Processando %d arquivo(s) do inbox", len(arquivos))

    resultados: list[dict] = []
    contadores = {"processado": 0, "duplicata": 0, "nao_identificado": 0, "erro": 0}

    for arquivo in arquivos:
        try:
            resultado = processar_arquivo(arquivo, diretorio_raw, diretorio_nao_identificados)
            resultados.append(resultado)
            contadores[resultado["status"]] += 1
        except Exception as erro:
            logger.error("Erro inesperado ao processar %s: %s", arquivo.name, erro)
            resultados.append(
                {
                    "arquivo_original": str(arquivo),
                    "destino": None,
                    "deteccao": None,
                    "status": "erro",
                }
            )
            contadores["erro"] += 1

    logger.info(
        "Processamento finalizado: %d processado(s), %d duplicata(s), "
        "%d não identificado(s), %d erro(s)",
        contadores["processado"],
        contadores["duplicata"],
        contadores["nao_identificado"],
        contadores["erro"],
    )

    return resultados


def main() -> None:
    """Ponto de entrada para execução via python -m src.inbox_processor."""
    diretorio_inbox = RAIZ_PROJETO / "inbox"
    diretorio_raw = RAIZ_PROJETO / "data" / "raw"

    logger.info("Iniciando processamento do inbox: %s", diretorio_inbox)

    resultados = processar_inbox(diretorio_inbox, diretorio_raw)

    if not resultados:
        logger.info("Nenhum arquivo processado")
        return

    for r in resultados:
        status = r["status"].upper()
        origem = Path(r["arquivo_original"]).name
        destino = r["destino"] or "N/A"
        logger.info("[%s] %s -> %s", status, origem, destino)


if __name__ == "__main__":
    main()


# "A liberdade é o reconhecimento da necessidade." -- Baruch Spinoza
