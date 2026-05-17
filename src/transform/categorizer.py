"""Categorização automática de transações via regras regex e overrides manuais."""

import re
from collections import Counter
from pathlib import Path
from typing import Optional

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("categorizer")


class Categorizer:
    """Aplica categorias e classificações a transações usando overrides e regras regex."""

    def __init__(
        self,
        caminho_regras: Optional[Path] = None,
        caminho_overrides: Optional[Path] = None,
    ) -> None:
        raiz_mappings = Path(__file__).parent.parent.parent / "mappings"

        if caminho_regras is None:
            caminho_regras = raiz_mappings / "categorias.yaml"
        if caminho_overrides is None:
            caminho_overrides = raiz_mappings / "overrides.yaml"

        self.overrides: list[dict] = []
        self.regras: list[dict] = []

        self._carregar_overrides(caminho_overrides)
        self._carregar_regras(caminho_regras)

    def _carregar_overrides(self, caminho: Path) -> None:
        """Carrega overrides manuais do YAML. Overrides têm prioridade sobre regex."""
        if not caminho.exists():
            logger.info("Arquivo de overrides não encontrado: %s", caminho)
            return

        with open(caminho, encoding="utf-8") as f:
            dados = yaml.safe_load(f)

        if not dados or "overrides" not in dados:
            logger.warning("Arquivo de overrides vazio ou sem chave 'overrides': %s", caminho)
            return

        for descricao, config in dados["overrides"].items():
            self.overrides.append(
                {
                    "descricao": str(descricao).strip(),
                    "categoria": config.get("categoria"),
                    "classificacao": config.get("classificacao"),
                    "tipo": config.get("tipo"),
                    "tag_irpf": config.get("tag_irpf"),
                    "regra_valor": config.get("regra_valor"),
                    # Filtros estruturais opcionais (Sprint INFRA-CATEGORIZAR-SALARIO-G4F-C6).
                    # Permitem matar drift de salario chegando como transferencia
                    # quando a descricao bruta nao contem o nome do empregador.  # noqa: accent
                    "banco_origem": config.get("banco_origem"),
                    "valor_min": config.get("valor_min"),
                    "valor_max": config.get("valor_max"),
                    "dia_min": config.get("dia_min"),
                    "dia_max": config.get("dia_max"),
                    "match_descricao_vazia": bool(config.get("match_descricao_vazia", False)),
                }
            )

        logger.info("Carregados %d overrides manuais", len(self.overrides))

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
        """Verifica se o valor atende à regra de valor (ex: '>=800', '<100').

        Sprint AUDIT-CATEGORIA-REGRA-VALOR-SINAL (2026-05-17): usa
        ``abs(valor)`` na comparação. ``regra_valor`` no YAML representa
        magnitude da transação (R$ 800), não sinal. Sem ``abs``,
        ``valor=-1000`` casava ``<800`` (porque -1000 < 800), fazendo TODA
        despesa KI-SABOR virar Padaria, nunca Aluguel. Despesa de R$ 1000
        e receita de R$ 1000 devem casar igualmente regras como ``>=800``.
        """
        if regra_valor is None:
            return True

        match = re.match(r"([<>=!]+)\s*(\d+\.?\d*)", regra_valor)
        if not match:
            return True

        operador, limite = match.groups()
        limite_float = float(limite)
        valor_abs = abs(valor)

        operacoes: dict[str, bool] = {
            ">=": valor_abs >= limite_float,
            "<=": valor_abs <= limite_float,
            ">": valor_abs > limite_float,
            "<": valor_abs < limite_float,
            "==": valor_abs == limite_float,
            "!=": valor_abs != limite_float,
        }

        return operacoes.get(operador, True)

    def _verificar_filtros_estruturais(self, override: dict, transacao: dict) -> bool:
        """Verifica filtros opcionais banco_origem/valor_min/valor_max/dia_min/dia_max.

        Retorna True se todos os filtros declarados forem atendidos (ou ausentes).
        Sprint INFRA-CATEGORIZAR-SALARIO-G4F-C6: salario G4F chega como transferencia
        no C6 com descricao sem nome do empregador; filtros estruturais sao a forma  # noqa: accent
        canonica de reconhecer o padrao por valor + banco + janela de data.
        """
        banco_esperado = override.get("banco_origem")
        if banco_esperado is not None:
            banco_atual = (transacao.get("banco_origem") or "").strip()
            if banco_atual.upper() != str(banco_esperado).strip().upper():
                return False

        valor = transacao.get("valor", 0) or 0
        valor_min = override.get("valor_min")
        valor_max = override.get("valor_max")
        if valor_min is not None and valor < float(valor_min):
            return False
        if valor_max is not None and valor > float(valor_max):
            return False

        dia_min = override.get("dia_min")
        dia_max = override.get("dia_max")
        if dia_min is not None or dia_max is not None:
            data_t = transacao.get("data")
            dia = getattr(data_t, "day", None)
            if dia is None:
                return False
            if dia_min is not None and dia < int(dia_min):
                return False
            if dia_max is not None and dia > int(dia_max):
                return False

        return True

    def _aplicar_override(self, transacao: dict) -> bool:
        """Tenta aplicar um override manual. Retorna True se encontrou match."""
        texto_busca = " ".join(
            [
                transacao.get("_descricao_original", "") or "",
                transacao.get("local", "") or "",
            ]
        ).upper()
        valor = transacao.get("valor", 0)

        for override in self.overrides:
            descricao_chave = override["descricao"].upper()
            descricao_vazia_ok = override.get("match_descricao_vazia", False)
            tem_filtros = (
                override.get("banco_origem") is not None
                or override.get("valor_min") is not None
                or override.get("valor_max") is not None
                or override.get("dia_min") is not None
                or override.get("dia_max") is not None
            )

            if descricao_vazia_ok and tem_filtros:
                # Match estritamente estrutural; ignora descrição.
                pass
            elif descricao_chave not in texto_busca:
                continue

            if not self._verificar_regra_valor(override["regra_valor"], valor):
                continue

            if not self._verificar_filtros_estruturais(override, transacao):
                continue

            if override["categoria"] is not None:
                transacao["categoria"] = override["categoria"]

            if override["tipo"] is not None:
                transacao["tipo"] = override["tipo"]

            # Classificação só é atribuída quando o tipo final é Despesa/Imposto.
            # Receita e Transferência Interna não são despesas classificáveis
            # (schema do projeto: classificação deve ser None nesses casos).
            if override["classificacao"] is not None:
                if transacao.get("tipo") in ("Despesa", "Imposto"):
                    transacao["classificacao"] = override["classificacao"]
                else:
                    logger.debug(
                        "Override '%s' ignorado para classificação: tipo=%s",
                        override["descricao"],
                        transacao.get("tipo"),
                    )

            if override["tag_irpf"] is not None:
                transacao["tag_irpf"] = override["tag_irpf"]

            return True

        return False

    def categorizar(self, transacao: dict) -> dict:
        """Aplica categoria e classificação a uma transação.

        Ordem de prioridade:
        1. Overrides manuais (overrides.yaml)
        2. Regras regex (categorias.yaml)
        3. Fallback para 'Outros' + 'Questionável'
        """
        if self._aplicar_override(transacao):
            self._garantir_classificacao(transacao)
            return transacao

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

            if regra["tipo"] is not None:
                transacao["tipo"] = regra["tipo"]

            # Classificação só é atribuída quando o tipo final é Despesa/Imposto.
            # Ver _aplicar_override para detalhe do schema.
            if regra["classificacao"] is not None:
                if transacao.get("tipo") in ("Despesa", "Imposto"):
                    transacao["classificacao"] = regra["classificacao"]

            if regra["tag_irpf"] is not None:
                transacao["tag_irpf"] = regra["tag_irpf"]

            break

        if transacao.get("categoria") is None:
            transacao["categoria"] = "Outros"
            if transacao.get("tipo") in ("Despesa", None):
                transacao["classificacao"] = "Questionável"

        self._garantir_classificacao(transacao)
        return transacao

    def _garantir_classificacao(self, transacao: dict) -> None:
        """Normaliza a classificação conforme o `tipo` final.

        Schema (Sprint 67): classificação só é válida para Despesa/Imposto.
        Receita e Transferência Interna têm classificação None (NaN no XLSX),
        pois não são despesas classificáveis. Qualquer valor residual
        herdado de regra/override genérico é sobrescrito aqui.
        """
        tipo = transacao.get("tipo", "")

        if tipo in ("Receita", "Transferência Interna"):
            transacao["classificacao"] = None
            return

        if tipo == "Imposto":
            if transacao.get("classificacao") is None:
                transacao["classificacao"] = "Obrigatório"
            return

        if transacao.get("classificacao") is None:
            transacao["classificacao"] = "Questionável"

    def _detectar_padroes_novos(self, transacoes: list[dict]) -> None:
        """Detecta descrições sem match que aparecem 3+ vezes (novos padrões)."""
        sem_match: list[str] = []
        for t in transacoes:
            if t.get("categoria") == "Outros":
                local = t.get("local", "").strip()
                if local:
                    sem_match.append(local.upper())

        contagem: Counter[str] = Counter(sem_match)
        padroes_recorrentes = {desc: qtd for desc, qtd in contagem.items() if qtd >= 3}

        if padroes_recorrentes:
            logger.warning("Novos padrões detectados (3+ ocorrências sem categorização):")
            for desc, qtd in sorted(padroes_recorrentes.items(), key=lambda x: -x[1]):
                logger.warning("  [%d ocorrências] %s", qtd, desc)

    def categorizar_lote(self, transacoes: list[dict]) -> list[dict]:
        """Categoriza uma lista de transações e detecta padrões novos."""
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

        self._detectar_padroes_novos(transacoes)

        return transacoes


# "A virtude está no meio." -- Aristóteles
