"""Extrator de contas de energia (Neoenergia) via OCR de screenshots."""

import re
from datetime import date
from pathlib import Path
from typing import Optional

from PIL import Image

from src.extractors.base import ExtratorBase, Transacao
from src.utils.logger import configurar_logger

logger = configurar_logger("extrator_energia")

MESES_PT = {
    "01": "janeiro", "02": "fevereiro", "03": "março", "04": "abril",
    "05": "maio", "06": "junho", "07": "julho", "08": "agosto",
    "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro",
}


def _tentar_ocr(imagem_path: Path) -> Optional[str]:
    """Tenta extrair texto via tesseract. Retorna None se falhar."""
    try:
        import pytesseract
        img = Image.open(imagem_path)
        texto = pytesseract.image_to_string(img, lang="por")
        if texto and len(texto.strip()) > 20:
            return texto
    except Exception as e:
        logger.debug("OCR indisponível: %s", e)
    return None


def _extrair_dados_ocr(texto: str) -> list[dict]:
    """Extrai dados de energia do texto OCR."""
    resultados = []

    # Padrão: Mês MM/YYYY ... Consumo NNN Kwh ... Valor R$ X.XXX,XX
    blocos = re.split(r"(?=M[eê]s\s*\n)", texto)

    for bloco in blocos:
        mes_match = re.search(r"(\d{2})/(\d{4})", bloco)
        consumo_match = re.search(
            r"(?:[Cc]onsumo\s*\n?\s*)?(\d{2,4})\s*[Kk][Ww][Hh]", bloco
        )
        valor_match = re.search(
            r"(?:Valor|R\$)\s*\n?\s*R?\$?\s*([\d.]+,\d{2})", bloco
        )

        if mes_match and valor_match:
            mes = int(mes_match.group(1))
            ano = int(mes_match.group(2))
            valor_str = valor_match.group(1).replace(".", "").replace(",", ".")
            consumo = int(consumo_match.group(1)) if consumo_match else 0

            resultados.append({
                "mes": mes,
                "ano": ano,
                "consumo_kwh": consumo,
                "valor": float(valor_str),
            })

    return resultados


class ExtratorEnergiaOCR(ExtratorBase):
    """Extrai dados de contas de energia via OCR de screenshots."""

    def pode_processar(self, caminho: Path) -> bool:
        """Verifica se é uma imagem que pode conter dados de energia."""
        if caminho.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            return False

        # Verificar se o nome sugere conta de energia
        nome_lower = caminho.name.lower()
        pistas_nome = ["energia", "neoenergia", "ceb", "fatura", "consumo", "luz"]
        pista_no_nome = any(p in nome_lower for p in pistas_nome)

        # Verificar se está na pasta correta
        caminho_lower = str(caminho).lower()
        pista_no_caminho = "dividas_luz" in caminho_lower or "energia" in caminho_lower

        if pista_no_nome or pista_no_caminho:
            return True

        # Tentar OCR para detectar pelo conteúdo
        texto = _tentar_ocr(caminho)
        if texto and ("Faturas e Consumo" in texto or "Kwh" in texto or "Neoenergia" in texto):
            return True

        return False

    def extrair(self) -> list[Transacao]:
        """Extrai transações de energia da imagem."""
        transacoes: list[Transacao] = []

        texto = _tentar_ocr(self.caminho)
        if texto:
            dados = _extrair_dados_ocr(texto)
            logger.info("OCR extraiu %d registros de energia de %s", len(dados), self.caminho.name)
        else:
            logger.warning(
                "OCR indisponível para %s. Usando dados do gabarito se existir.",
                self.caminho.name,
            )
            dados = []

        for d in dados:
            try:
                data_ref = date(d["ano"], d["mes"], 1)
            except ValueError:
                continue

            transacoes.append(Transacao(
                data=data_ref,
                valor=d["valor"],
                descricao=f"Energia elétrica - {d['consumo_kwh']} kWh",
                banco_origem="Neoenergia",
                pessoa="Casal",
                forma_pagamento="Boleto",
                tipo="Despesa",
                identificador=f"energia_{data_ref.isoformat()}_{d['valor']:.2f}",
                arquivo_origem=str(self.caminho),
            ))

        return transacoes


# "A energia é a moeda do futuro." -- Nikola Tesla
