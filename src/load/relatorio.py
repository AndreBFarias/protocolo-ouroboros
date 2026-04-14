"""Geração de relatório mensal em Markdown."""

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Optional

from src.utils.logger import configurar_logger

logger = configurar_logger("relatorio")


def _agrupar_por_mes(transacoes: list[dict]) -> dict[str, list[dict]]:
    """Agrupa transações por mes_ref."""
    por_mes: dict[str, list[dict]] = {}
    for t in transacoes:
        mes = t.get("mes_ref", "")
        por_mes.setdefault(mes, []).append(t)
    return por_mes


def _formatar_valor(valor: float) -> str:
    """Formata valor monetário no padrão brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_relatorio_mes(
    transacoes: list[dict],
    mes_ref: str,
    transacoes_mes_anterior: Optional[list[dict]] = None,
) -> str:
    """Gera o relatório markdown de um mês específico."""
    # Filtrar transações do mês (excluir transferências internas)
    transacoes_mes = [
        t for t in transacoes
        if t.get("mes_ref") == mes_ref and t.get("tipo") != "Transferência Interna"
    ]
    transferencias = [
        t for t in transacoes
        if t.get("mes_ref") == mes_ref and t.get("tipo") == "Transferência Interna"
    ]

    receitas = sum(t["valor"] for t in transacoes_mes if t.get("tipo") == "Receita")
    despesas = sum(t["valor"] for t in transacoes_mes if t.get("tipo") in ("Despesa", "Imposto"))
    saldo = receitas - despesas

    # Top 5 categorias
    gastos_categoria: dict[str, float] = {}
    for t in transacoes_mes:
        if t.get("tipo") in ("Despesa", "Imposto"):
            cat = t.get("categoria", "Outros")
            gastos_categoria[cat] = gastos_categoria.get(cat, 0) + t["valor"]

    top_categorias = sorted(gastos_categoria.items(), key=lambda x: x[1], reverse=True)[:5]

    # Classificações
    obrigatorio = sum(
        t["valor"] for t in transacoes_mes
        if t.get("classificacao") == "Obrigatório" and t.get("tipo") in ("Despesa", "Imposto")
    )
    questionavel = sum(
        t["valor"] for t in transacoes_mes
        if t.get("classificacao") == "Questionável" and t.get("tipo") in ("Despesa", "Imposto")
    )
    superfluo = sum(
        t["valor"] for t in transacoes_mes
        if t.get("classificacao") == "Supérfluo" and t.get("tipo") in ("Despesa", "Imposto")
    )

    # Sem categoria
    sem_categoria = [t for t in transacoes_mes if t.get("categoria") == "Outros"]

    # Montar relatório
    linhas = [
        f"# Relatório Financeiro -- {mes_ref}",
        "",
        "---",
        "",
        "## Resumo",
        "",
        f"- Receita: {_formatar_valor(receitas)}",
        f"- Despesa: {_formatar_valor(despesas)}",
        f"- Saldo: {_formatar_valor(saldo)}",
        "",
    ]

    # Comparativo com mês anterior
    if transacoes_mes_anterior:
        desp_ant = sum(
            t["valor"] for t in transacoes_mes_anterior
            if t.get("tipo") in ("Despesa", "Imposto")
            and t.get("tipo") != "Transferência Interna"
        )
        diff = despesas - desp_ant
        sinal = "+" if diff > 0 else ""
        linhas.append(f"- Variação vs mês anterior: {sinal}{_formatar_valor(diff)}")
        linhas.append("")

    # Top 5 categorias
    linhas.extend([
        "## Top 5 Categorias de Gasto",
        "",
        "| Categoria | Valor | % do total |",
        "|-----------|-------|-----------|",
    ])
    for cat, valor in top_categorias:
        pct = (valor / despesas * 100) if despesas > 0 else 0
        linhas.append(f"| {cat} | {_formatar_valor(valor)} | {pct:.1f}% |")
    linhas.append("")

    # Classificação
    linhas.extend([
        "## Por Classificação",
        "",
        f"- Obrigatório: {_formatar_valor(obrigatorio)}",
        f"- Questionável: {_formatar_valor(questionavel)}",
        f"- Supérfluo: {_formatar_valor(superfluo)}",
        "",
    ])

    # Alertas
    linhas.extend(["## Alertas", ""])
    if len(sem_categoria) > 0:
        linhas.append(f"- {len(sem_categoria)} transações sem categoria reconhecida")
    if superfluo > 500:
        linhas.append(f"- Gastos supérfluos acima de R$ 500: {_formatar_valor(superfluo)}")
    if saldo < 0:
        linhas.append(f"- [ALERTA] Saldo negativo no mês: {_formatar_valor(saldo)}")
    if not any("ALERTA" in l or "transações" in l for l in linhas[-3:]):
        linhas.append("- Nenhum alerta crítico")
    linhas.append("")

    # Transferências internas
    total_transf = sum(t["valor"] for t in transferencias)
    linhas.extend([
        "## Transferências Internas",
        "",
        f"- Total movimentado entre contas: {_formatar_valor(total_transf)}",
        f"- Quantidade: {len(transferencias)} transações",
        "",
    ])

    # Transações por pessoa
    gastos_andre = sum(
        t["valor"] for t in transacoes_mes
        if t.get("quem") == "André" and t.get("tipo") in ("Despesa", "Imposto")
    )
    gastos_vitoria = sum(
        t["valor"] for t in transacoes_mes
        if t.get("quem") == "Vitória" and t.get("tipo") in ("Despesa", "Imposto")
    )
    linhas.extend([
        "## Gastos por Pessoa",
        "",
        f"- André: {_formatar_valor(gastos_andre)}",
        f"- Vitória: {_formatar_valor(gastos_vitoria)}",
        "",
    ])

    linhas.extend([
        "---",
        "",
        f"*Gerado automaticamente em {date.today().isoformat()}*",
    ])

    return "\n".join(linhas)


def gerar_relatorios(
    transacoes: list[dict],
    diretorio_saida: Path,
) -> list[Path]:
    """Gera relatórios para todos os meses disponíveis."""
    diretorio_saida.mkdir(parents=True, exist_ok=True)
    por_mes = _agrupar_por_mes(transacoes)
    meses_ordenados = sorted(por_mes.keys())

    arquivos_gerados: list[Path] = []

    for i, mes in enumerate(meses_ordenados):
        mes_anterior = por_mes.get(meses_ordenados[i - 1]) if i > 0 else None
        conteudo = gerar_relatorio_mes(transacoes, mes, mes_anterior)

        caminho = diretorio_saida / f"{mes}_relatorio.md"
        caminho.write_text(conteudo, encoding="utf-8")
        arquivos_gerados.append(caminho)

    logger.info("Relatórios gerados: %d meses em %s", len(arquivos_gerados), diretorio_saida)
    return arquivos_gerados


# "Não é o que acontece com você, mas como você reage que importa." -- Epicteto
