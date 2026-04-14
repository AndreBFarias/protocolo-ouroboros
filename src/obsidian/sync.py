"""Sincronizacao de relatorios financeiros com o vault Obsidian."""

import re
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("obsidian_sync")

VAULT_PATH: Path = Path.home() / "Controle de Bordo"
FINANCEIRO_PATH: Path = VAULT_PATH / "Pessoal" / "Financeiro"
RELATORIOS_PATH: Path = FINANCEIRO_PATH / "Relatorios"
METAS_PATH: Path = FINANCEIRO_PATH / "Metas"
PROJETO_ROOT: Path = Path(__file__).parent.parent.parent
OUTPUT_PATH: Path = PROJETO_ROOT / "data" / "output"
METAS_YAML: Path = PROJETO_ROOT / "mappings" / "metas.yaml"

def _formatar_moeda(valor: float) -> str:
    """Formata valor monetario no padrao brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


MESES_PT: dict[str, str] = {
    "01": "Janeiro",
    "02": "Fevereiro",
    "03": "Marco",
    "04": "Abril",
    "05": "Maio",
    "06": "Junho",
    "07": "Julho",
    "08": "Agosto",
    "09": "Setembro",
    "10": "Outubro",
    "11": "Novembro",
    "12": "Dezembro",
}


def _extrair_valores_relatorio(conteudo: str) -> dict[str, Optional[float]]:
    """Extrai receita, despesa e saldo do conteudo do relatorio."""
    valores: dict[str, Optional[float]] = {
        "receita": None,
        "despesa": None,
        "saldo": None,
    }

    padroes = {
        "receita": r"Receita:\s*R\$\s*([\d.,]+)",
        "despesa": r"Despesa:\s*R\$\s*([\d.,]+)",
        "saldo": r"Saldo:\s*R\$\s*(-?[\d.,]+)",
    }

    for chave, padrao in padroes.items():
        match = re.search(padrao, conteudo)
        if match:
            valor_str = match.group(1).replace(".", "").replace(",", ".")
            try:
                valores[chave] = float(valor_str)
            except ValueError:
                logger.warning("Valor invalido para %s: %s", chave, match.group(1))

    return valores


def _nome_mes_pt(mes_ref: str) -> str:
    """Retorna o nome do mes em portugues a partir de YYYY-MM."""
    partes = mes_ref.split("-")
    if len(partes) != 2:
        return mes_ref
    numero_mes = partes[1]
    return MESES_PT.get(numero_mes, mes_ref)


def _gerar_frontmatter(mes_ref: str, valores: dict[str, Optional[float]]) -> str:
    """Gera o frontmatter YAML para um relatorio mensal."""
    partes = mes_ref.split("-")
    ano = partes[0] if len(partes) == 2 else mes_ref
    nome_mes = _nome_mes_pt(mes_ref)

    frontmatter_dict: dict[str, object] = {
        "tipo": "relatorio_mensal",
        "mes": mes_ref,
    }

    if valores["receita"] is not None:
        frontmatter_dict["receita"] = valores["receita"]
    if valores["despesa"] is not None:
        frontmatter_dict["despesa"] = valores["despesa"]
    if valores["saldo"] is not None:
        frontmatter_dict["saldo"] = valores["saldo"]

    frontmatter_dict["tags"] = ["financeiro", "mensal", "relatorio"]
    frontmatter_dict["aliases"] = [
        f"Relatorio {nome_mes} {ano}",
        f"Financas {nome_mes}",
    ]
    frontmatter_dict["created"] = date.today().isoformat()

    linhas = ["---"]
    for chave, valor in frontmatter_dict.items():
        if isinstance(valor, list):
            itens = ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in valor)
            linhas.append(f"{chave}: [{itens}]")
        elif isinstance(valor, str):
            linhas.append(f'{chave}: "{valor}"')
        elif isinstance(valor, float):
            linhas.append(f"{chave}: {valor}")
        else:
            linhas.append(f"{chave}: {valor}")
    linhas.append("---")

    return "\n".join(linhas)


def _gerar_backlinks(metas: list[dict[str, object]]) -> str:
    """Gera secao de backlinks para metas financeiras."""
    linhas = ["", "## Links"]
    for meta in metas:
        nome = str(meta.get("nome", ""))
        nome_formatado = nome.title().replace(" ", " ")
        linhas.append(f"- [[{nome_formatado}]]")
    return "\n".join(linhas)


def _remover_linha_gerado(conteudo: str) -> str:
    """Remove a linha de 'Gerado automaticamente' do conteudo original."""
    linhas = conteudo.split("\n")
    linhas_filtradas = [
        linha for linha in linhas
        if not linha.strip().startswith("*Gerado automaticamente")
    ]
    return "\n".join(linhas_filtradas).rstrip()


def _carregar_metas() -> list[dict[str, object]]:
    """Carrega metas do arquivo YAML."""
    if not METAS_YAML.exists():
        logger.warning("Arquivo de metas nao encontrado: %s", METAS_YAML)
        return []

    with METAS_YAML.open("r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)

    return dados.get("metas", []) if dados else []


def sincronizar_relatorios(diretorio_output: Path) -> list[Path]:
    """Copia relatorios MD do pipeline para o vault Obsidian.

    Para cada relatorio YYYY-MM_relatorio.md:
    1. Adiciona frontmatter YAML (tags, tipo, aliases, datas)
    2. Adiciona backlinks para metas e dividas
    3. Copia para VAULT/Pessoal/Financeiro/Relatorios/YYYY-MM.md
    """
    RELATORIOS_PATH.mkdir(parents=True, exist_ok=True)

    metas = _carregar_metas()
    arquivos_relatorio = sorted(diretorio_output.glob("*_relatorio.md"))

    if not arquivos_relatorio:
        logger.warning("Nenhum relatorio encontrado em %s", diretorio_output)
        return []

    copiados: list[Path] = []

    for arquivo in arquivos_relatorio:
        mes_ref = arquivo.stem.replace("_relatorio", "")
        conteudo_original = arquivo.read_text(encoding="utf-8")

        valores = _extrair_valores_relatorio(conteudo_original)
        frontmatter = _gerar_frontmatter(mes_ref, valores)
        conteudo_limpo = _remover_linha_gerado(conteudo_original)
        backlinks = _gerar_backlinks(metas)

        conteudo_final = f"{frontmatter}\n\n{conteudo_limpo}\n{backlinks}\n"

        destino = RELATORIOS_PATH / f"{mes_ref}.md"
        destino.write_text(conteudo_final, encoding="utf-8")
        copiados.append(destino)

    logger.info(
        "Relatorios sincronizados: %d arquivos em %s",
        len(copiados),
        RELATORIOS_PATH,
    )
    return copiados


def criar_notas_metas() -> list[Path]:
    """Cria notas de metas financeiras no vault Obsidian."""
    METAS_PATH.mkdir(parents=True, exist_ok=True)
    metas = _carregar_metas()

    if not metas:
        logger.warning("Nenhuma meta encontrada para criar notas")
        return []

    criadas: list[Path] = []

    for meta in metas:
        nome = str(meta.get("nome", "Sem nome"))
        valor_alvo = meta.get("valor_alvo", 0)
        valor_atual = meta.get("valor_atual", 0)
        prioridade = meta.get("prioridade", 99)
        prazo = meta.get("prazo", "Indefinido")
        tipo_meta = meta.get("tipo", "monetaria")
        nota = meta.get("nota", "")
        depende_de = meta.get("depende_de", [])

        nome_arquivo = nome.title().replace(" ", " ")

        frontmatter_linhas = [
            "---",
            "tipo: meta_financeira",
            f'nome: "{nome}"',
        ]

        if tipo_meta != "binario":
            frontmatter_linhas.append(f"valor_alvo: {valor_alvo}")
            frontmatter_linhas.append(f"valor_atual: {valor_atual}")

        frontmatter_linhas.extend([
            f"prioridade: {prioridade}",
            f'prazo: "{prazo}"',
            'tags: ["financeiro", "meta"]',
            "---",
        ])

        corpo_linhas = [
            "",
            f"# {nome.title()}",
            "",
        ]

        if tipo_meta == "binario":
            corpo_linhas.append("Tipo: Meta binaria (sim/nao)")
            corpo_linhas.append(f"Prazo: {prazo}")
        else:
            valor_alvo_fmt = _formatar_moeda(valor_alvo)
            progresso = (valor_atual / valor_alvo * 100) if valor_alvo > 0 else 0
            corpo_linhas.append(f"Valor alvo: {valor_alvo_fmt}")
            corpo_linhas.append(f"Progresso: {progresso:.0f}%")

        if nota:
            corpo_linhas.extend(["", f"Nota: {nota}"])

        if depende_de:
            corpo_linhas.extend(["", "### Dependencias"])
            for dep in depende_de:
                corpo_linhas.append(f"- {dep}")

        corpo_linhas.extend([
            "",
            "## Relatorios relacionados",
            "",
            "```dataview",
            "LIST",
            'FROM "Pessoal/Financeiro/Relatorios"',
            "SORT file.name DESC",
            "LIMIT 6",
            "```",
        ])

        conteudo = "\n".join(frontmatter_linhas) + "\n".join(corpo_linhas) + "\n"

        destino = METAS_PATH / f"{nome_arquivo}.md"
        destino.write_text(conteudo, encoding="utf-8")
        criadas.append(destino)
        logger.info("Nota de meta criada: %s", destino.name)

    logger.info("Notas de metas criadas: %d em %s", len(criadas), METAS_PATH)
    return criadas


def criar_moc_financeiro() -> Path:
    """Cria nota MOC (Map of Content) do dashboard financeiro."""
    conteudo = """---
tipo: moc
hub: pessoal
tags: ["financeiro", "dashboard", "moc"]
---

# Dashboard Financeiro

## Relatorios Recentes

```dataview
TABLE receita, despesa, saldo
FROM "Pessoal/Financeiro/Relatorios"
SORT mes DESC
LIMIT 6
```

## Metas

```dataview
TABLE valor_alvo, valor_atual, prazo
FROM "Pessoal/Financeiro/Metas"
SORT prioridade ASC
```

## Navegacao

- [[Pessoal/Financeiro/Relatorios|Todos os Relatorios]]
- [[Pessoal/Financeiro/Metas|Todas as Metas]]
"""

    destino = FINANCEIRO_PATH / "Dashboard Financeiro.md"
    destino.write_text(conteudo, encoding="utf-8")
    logger.info("MOC financeiro criado: %s", destino)
    return destino


def executar_sincronizacao() -> None:
    """Executa o fluxo completo de sincronizacao com o vault Obsidian."""
    logger.info("Iniciando sincronizacao com vault Obsidian")
    logger.info("Vault: %s", VAULT_PATH)
    logger.info("Output: %s", OUTPUT_PATH)

    if not VAULT_PATH.exists():
        logger.error("Vault Obsidian nao encontrado em %s", VAULT_PATH)
        return

    if not OUTPUT_PATH.exists():
        logger.error("Diretorio de output nao encontrado em %s", OUTPUT_PATH)
        return

    relatorios = sincronizar_relatorios(OUTPUT_PATH)
    logger.info("Relatorios sincronizados: %d", len(relatorios))

    metas = criar_notas_metas()
    logger.info("Notas de metas criadas: %d", len(metas))

    moc = criar_moc_financeiro()
    logger.info("MOC criado: %s", moc)

    logger.info("Sincronizacao concluida com sucesso")


if __name__ == "__main__":
    executar_sincronizacao()


# "Nao e porque as coisas sao dificeis que nao ousamos;
# e porque nao ousamos que sao dificeis." -- Seneca
