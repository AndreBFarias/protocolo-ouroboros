"""Categorização automática de transações via regras regex."""

import re
from pathlib import Path
from typing import Optional

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("categorizer")


class Categorizer:
    """Aplica categorias e classificações a transações usando regras regex."""

    def __init__(self, caminho_regras: Optional[Path] = None):
        if caminho_regras is None:
            caminho_regras = Path(__file__).parent.parent.parent / "mappings" / "categorias.yaml"

        self.regras: list[dict] = []
        self._carregar_regras(caminho_regras)

    def _carregar_regras(self, caminho: Path) -> None:
        """Carrega regras de categorização do YAML."""
        if not caminho.exists():
            logger.warning("Arquivo de regras não encontrado: %s", caminho)
            return

        with open(caminho, encoding="utf-8") as f:
            dados = yaml.safe_load(f)

        if not dados or "regras" not in dados:
            logger.warning("Arquivo de regras vazio ou sem chave 'regras': %s", caminho)
            return

        for nome, regra in dados["regras"].items():
            regex_str = regra.get("regex", "")
            try:
                regex_compilado = re.compile(regex_str, re.IGNORECASE)
            except re.error as e:
                logger.error("Regex inválido em regra '%s': %s", nome, e)
                continue

            self.regras.append(
                {
                    "nome": nome,
                    "regex": regex_compilado,
                    "categoria": regra.get("categoria"),
                    "classificacao": regra.get("classificacao"),
                    "tipo": regra.get("tipo"),
                    "tag_irpf": regra.get("tag_irpf"),
                    "regra_valor": regra.get("regra_valor"),
                }
            )

        logger.info("Carregadas %d regras de categorização", len(self.regras))

    def _verificar_regra_valor(self, regra_valor: Optional[str], valor: float) -> bool:
        """Verifica se o valor atende à regra de valor (ex: '>=800', '<100')."""
        if regra_valor is None:
            return True

        match = re.match(r"([<>=!]+)\s*(\d+\.?\d*)", regra_valor)
        if not match:
            return True

        operador, limite = match.groups()
        limite_float = float(limite)

        operacoes = {
            ">=": valor >= limite_float,
            "<=": valor <= limite_float,
            ">": valor > limite_float,
            "<": valor < limite_float,
            "==": valor == limite_float,
            "!=": valor != limite_float,
        }

        return operacoes.get(operador, True)

    def categorizar(self, transacao: dict) -> dict:
        """Aplica categoria e classificação a uma transação.

        Busca na descrição original e no local. Primeira regra que casar é aplicada.
        """
        texto_busca = " ".join(
            [
                transacao.get("_descricao_original", ""),
                transacao.get("local", ""),
            ]
        )
        valor = transacao.get("valor", 0)

        for regra in self.regras:
            if not regra["regex"].search(texto_busca):
                continue

            if not self._verificar_regra_valor(regra["regra_valor"], valor):
                continue

            if regra["categoria"] is not None:
                transacao["categoria"] = regra["categoria"]

            if regra["classificacao"] is not None:
                transacao["classificacao"] = regra["classificacao"]

            if regra["tipo"] is not None:
                transacao["tipo"] = regra["tipo"]

            if regra["tag_irpf"] is not None:
                transacao["tag_irpf"] = regra["tag_irpf"]

            break

        # Fallback: sem categoria reconhecida
        if transacao.get("categoria") is None:
            transacao["categoria"] = "Outros"
            transacao["classificacao"] = "Questionável"

        # Garantir que classificação nunca fique nula
        if transacao.get("classificacao") is None:
            tipo = transacao.get("tipo", "")
            if tipo == "Transferência Interna":
                transacao["classificacao"] = "N/A"
            elif tipo == "Receita":
                transacao["classificacao"] = "N/A"
            elif tipo == "Imposto":
                transacao["classificacao"] = "Obrigatório"
            else:
                transacao["classificacao"] = "Questionável"

        return transacao

    def categorizar_lote(self, transacoes: list[dict]) -> list[dict]:
        """Categoriza uma lista de transações."""
        categorizadas = 0
        sem_categoria = 0

        for t in transacoes:
            self.categorizar(t)
            if t["categoria"] != "Outros":
                categorizadas += 1
            else:
                sem_categoria += 1

        total = len(transacoes)
        if total > 0:
            pct = (categorizadas / total) * 100
            logger.info(
                "Categorização: %d/%d (%.1f%%) categorizadas, %d sem categoria",
                categorizadas,
                total,
                pct,
                sem_categoria,
            )

        return transacoes


# "A virtude está no meio." -- Aristóteles
