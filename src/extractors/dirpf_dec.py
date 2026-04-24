"""Extrator de declaração IRPF (.DEC) da Receita Federal (P3.1).

DEC é o formato proprietário que o programa da Receita exporta. É texto
plano ASCII com layout fixed-width:

  Linha 1:  IRPF<ano_exerc>(4)<ano_base>(4)<código>(5)<cpf>(11)<nome>(...)
  Linhas N: <secao>(2)<cpf>(11)<campos fixed-width>

MVP (P3.1 auditoria 2026-04-23): extrai apenas cabeçalho (CPF + anos +
nome + flag RETIF do nome do arquivo) e ingere como node `documento`
tipo `dirpf` no grafo. Não parseia rendimentos/dedutíveis individuais
(seções 17/18/19/20 etc.) -- isso fica para sprint dedicada com layout
oficial da SRF em mãos.

Chave canônica: `DIRPF|<cpf>|<ano_base>[_RETIF]`. Idempotente por
re-ingestão. tipo_documento = "dirpf" (original) ou "dirpf_retif"
(retificadora).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from src.extractors.base import ExtratorBase, Transacao
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.utils.logger import configurar_logger

logger = configurar_logger("dirpf_dec")

EXTENSOES_ACEITAS: tuple[str, ...] = (".dec",)

# Layout linha 1: "IRPF    202620253600105127373122   1999ANDRE DA SILVA..."
# - "IRPF" + espaços variáveis
# - 4 dígitos ano-exercício
# - 4 dígitos ano-base
# - 5 dígitos código programa
# - 11 dígitos CPF
# - espaços + nome em até ~60 chars
_RE_CABECALHO = re.compile(
    r"^IRPF\s+(\d{4})(\d{4})(\d{5})(\d{11})\s+\d+([A-Z][A-Z\s]+?)\s{3,}",
    re.MULTILINE,
)


def _detectar_retif_do_nome(caminho: Path) -> bool:
    """RETIF ou RETIFICADORA no nome do arquivo sinaliza declaração retificadora."""
    nome = caminho.name.upper()
    return "RETIF" in nome


def _montar_documento(texto: str, caminho: Path) -> dict[str, Any]:
    m = _RE_CABECALHO.search(texto)
    if not m:
        return {}
    ano_exerc, ano_base, _codigo, cpf, nome_raw = m.groups()
    nome = nome_raw.strip()
    if not nome or not cpf:
        return {}

    retif = _detectar_retif_do_nome(caminho)
    tipo_doc = "dirpf_retif" if retif else "dirpf"
    chave_sufixo = "_RETIF" if retif else ""
    chave = f"DIRPF|{cpf}|{ano_base}{chave_sufixo}"

    # CNPJ sintético derivado do CPF (Receita não tem CNPJ emitente próprio
    # para DIRPF -- a pessoa física declarante ocupa o papel de fornecedor).
    cpf_sintetico = f"DIRPF|{hashlib.sha256(cpf.encode('utf-8')).hexdigest()[:12]}"

    return {
        "chave_44": chave,
        "cnpj_emitente": cpf_sintetico,
        "data_emissao": f"{ano_exerc}-04-30",  # prazo canônico de entrega
        "tipo_documento": tipo_doc,
        "total": 0.0,  # valores individuais não parseados no MVP
        "razao_social": nome,
        "numero": chave,
        "arquivo_original": str(caminho.resolve()),
        "periodo_apuracao": f"{ano_base}-12",  # referência: ano-base inteiro
        "cpf_declarante": cpf,
        "ano_base": ano_base,
        "ano_exercicio": ano_exerc,
    }


class ExtratorDIRPFDec(ExtratorBase):
    """Extrai cabeçalho da declaração IRPF .DEC e ingere node `documento`."""

    BANCO_ORIGEM: str = "DIRPF"

    def __init__(self, caminho: Path, grafo: GrafoDB | None = None) -> None:
        super().__init__(caminho)
        self._grafo = grafo

    def pode_processar(self, caminho: Path) -> bool:
        return caminho.suffix.lower() in EXTENSOES_ACEITAS

    def extrair(self) -> list[Transacao]:
        try:
            resultado = self.extrair_dirpf(self.caminho)
        except Exception as erro:  # noqa: BLE001
            self.logger.error("falha ao extrair DIRPF %s: %s", self.caminho.name, erro)
            return []

        documento = resultado["documento"]
        if not documento:
            self.logger.warning(
                "DIRPF %s sem cabeçalho parseável; não ingerido",
                self.caminho.name,
            )
            return []

        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo = self._grafo is None
        try:
            grafo.criar_schema()
            ingerir_documento_fiscal(grafo, documento, itens=[], caminho_arquivo=self.caminho)
        except ValueError as erro_ing:
            self.logger.warning("DIRPF inválido em %s: %s", self.caminho.name, erro_ing)
        finally:
            if criou_grafo:
                grafo.fechar()

        self.logger.info(
            "DIRPF ingerido: %s (CPF=%s ano_base=%s retif=%s)",
            self.caminho.name,
            documento.get("cpf_declarante"),
            documento.get("ano_base"),
            documento.get("tipo_documento") == "dirpf_retif",
        )
        return []

    def extrair_dirpf(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> dict[str, Any]:
        if texto_override is not None:
            texto = texto_override
        else:
            texto = caminho.read_text(encoding="latin-1", errors="replace")

        if len(texto.strip()) < 50:
            return {"documento": {}, "texto": texto, "_erro_extracao": "texto_vazio"}

        documento = _montar_documento(texto, caminho)
        erro: str | None = None if documento else "cabecalho_nao_parseavel"
        return {"documento": documento, "texto": texto, "_erro_extracao": erro}


# "A declaração honesta é a única que não precisa ser recalculada." -- princípio fiscal
