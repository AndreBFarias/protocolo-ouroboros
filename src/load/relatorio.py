"""Geração de relatório mensal em Markdown."""

from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("relatorio")

CAMINHO_METAS: Path = Path(__file__).resolve().parents[2] / "mappings" / "metas.yaml"


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


def _carregar_metas() -> list[dict[str, Any]]:
    """Carrega metas do arquivo YAML."""
    if not CAMINHO_METAS.exists():
        return []
    try:
        with open(CAMINHO_METAS, encoding="utf-8") as f:
            dados = yaml.safe_load(f)
        return dados.get("metas", [])
    except Exception as e:
        logger.warning("Erro ao carregar metas: %s", e)
        return []


def _barra_progresso_ascii(progresso: float, largura: int = 20) -> str:
    """Gera barra de progresso ASCII. Progresso de 0.0 a 1.0."""
    preenchido = int(progresso * largura)
    vazio = largura - preenchido
    return f"[{'#' * preenchido}{'.' * vazio}] {progresso * 100:.0f}%"


def _gerar_secao_metas() -> list[str]:
    """Gera seção de metas com barras de progresso ASCII."""
    metas = _carregar_metas()
    if not metas:
        return []

    linhas: list[str] = ["## Metas", ""]

    for meta in sorted(metas, key=lambda m: m.get("prioridade", 99)):
        nome = meta.get("nome", "Sem nome")
        prazo = meta.get("prazo", "")
        prioridade = meta.get("prioridade", 0)
        nota = meta.get("nota", "")
        tipo = meta.get("tipo", "valor")

        if tipo == "binario":
            linhas.append(f"- **{nome}** (P{prioridade}) -- Prazo: {prazo} -- [ ] Pendente")
        else:
            valor_alvo = meta.get("valor_alvo", 0)
            valor_atual = meta.get("valor_atual", 0)
            progresso = min(valor_atual / valor_alvo, 1.0) if valor_alvo > 0 else 0.0
            barra = _barra_progresso_ascii(progresso)
            linhas.append(
                f"- **{nome}** (P{prioridade}) -- "
                f"{_formatar_valor(valor_atual)} / {_formatar_valor(valor_alvo)} -- "
                f"Prazo: {prazo}"
            )
            linhas.append(f"  {barra}")

        if nota:
            linhas.append(f"  *{nota}*")

        deps = meta.get("depende_de", [])
        if deps:
            linhas.append(f"  Depende de: {', '.join(deps)}")

    linhas.append("")
    return linhas


def _gerar_secao_projecao(transacoes: list[dict], mes_ref: str) -> list[str]:
    """Gera seção de projeção calculando ritmo e estimativas."""
    transacoes_validas = [
        t for t in transacoes
        if t.get("tipo") != "Transferência Interna" and t.get("mes_ref")
    ]

    if not transacoes_validas:
        return []

    meses_disponiveis = sorted({t["mes_ref"] for t in transacoes_validas}, reverse=True)
    ultimos_3 = meses_disponiveis[:3]

    recentes = [t for t in transacoes_validas if t.get("mes_ref") in ultimos_3]
    n_meses = len(ultimos_3) or 1

    receita_total = sum(t["valor"] for t in recentes if t.get("tipo") == "Receita")
    despesa_total = sum(
        t["valor"] for t in recentes if t.get("tipo") in ("Despesa", "Imposto")
    )

    receita_media = receita_total / n_meses
    despesa_media = despesa_total / n_meses
    saldo_medio = receita_media - despesa_media

    projecao_6m = saldo_medio * 6
    projecao_12m = saldo_medio * 12

    linhas: list[str] = [
        "## Projeção",
        "",
        f"- Receita média (últimos {n_meses} meses): {_formatar_valor(receita_media)}",
        f"- Despesa média (últimos {n_meses} meses): {_formatar_valor(despesa_media)}",
        f"- Saldo médio mensal: {_formatar_valor(saldo_medio)}",
        "",
    ]

    if saldo_medio > 0:
        linhas.append(f"- Projeção 6 meses (acumulado): {_formatar_valor(projecao_6m)}")
        linhas.append(f"- Projeção 12 meses (acumulado): {_formatar_valor(projecao_12m)}")
        linhas.append("")
        linhas.append(
            "Se mantiver o ritmo atual, sobram "
            f"{_formatar_valor(projecao_6m)} em 6 meses e "
            f"{_formatar_valor(projecao_12m)} em 12 meses."
        )
    else:
        linhas.append(f"- Projeção 6 meses (déficit): {_formatar_valor(projecao_6m)}")
        linhas.append(f"- Projeção 12 meses (déficit): {_formatar_valor(projecao_12m)}")
        linhas.append("")
        linhas.append(
            "**ALERTA:** No ritmo atual, faltam "
            f"{_formatar_valor(abs(projecao_6m))} em 6 meses e "
            f"{_formatar_valor(abs(projecao_12m))} em 12 meses."
        )

    linhas.append("")
    return linhas


def _gerar_secao_irpf(transacoes: list[dict], mes_ref: str) -> list[str]:
    """Gera seção de IRPF acumulado no ano."""
    ano = mes_ref[:4]
    transacoes_ano = [
        t for t in transacoes
        if t.get("mes_ref", "").startswith(ano) and t.get("tipo") != "Transferência Interna"
    ]

    if not transacoes_ano:
        return []

    rendimentos_tributaveis = sum(
        t["valor"] for t in transacoes_ano
        if t.get("tipo") == "Receita" and t.get("categoria") in ("Salário", "Renda PJ")
    )

    despesas_dedutiveis = sum(
        t["valor"] for t in transacoes_ano
        if t.get("tag_irpf") == "dedutivel_medico"
    )

    impostos_pagos = sum(
        t["valor"] for t in transacoes_ano
        if t.get("tipo") == "Imposto" or t.get("tag_irpf") == "imposto_pago"
    )

    linhas: list[str] = [
        f"## IRPF Acumulado ({ano})",
        "",
        f"- Rendimentos tributáveis (Salário + PJ): {_formatar_valor(rendimentos_tributaveis)}",
        f"- Despesas dedutíveis (saúde): {_formatar_valor(despesas_dedutiveis)}",
        f"- Impostos pagos (DARF/DAS): {_formatar_valor(impostos_pagos)}",
        "",
    ]

    return linhas


def gerar_relatorio_mes(
    transacoes: list[dict],
    mes_ref: str,
    transacoes_mes_anterior: Optional[list[dict]] = None,
) -> str:
    """Gera o relatório markdown de um mês específico."""
    # Filtrar transações do mês (excluir transferências internas)
    transacoes_mes = [
        t
        for t in transacoes
        if t.get("mes_ref") == mes_ref and t.get("tipo") != "Transferência Interna"
    ]
    transferencias = [
        t
        for t in transacoes
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
        t["valor"]
        for t in transacoes_mes
        if t.get("classificacao") == "Obrigatório" and t.get("tipo") in ("Despesa", "Imposto")
    )
    questionavel = sum(
        t["valor"]
        for t in transacoes_mes
        if t.get("classificacao") == "Questionável" and t.get("tipo") in ("Despesa", "Imposto")
    )
    superfluo = sum(
        t["valor"]
        for t in transacoes_mes
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
            t["valor"]
            for t in transacoes_mes_anterior
            if t.get("tipo") in ("Despesa", "Imposto") and t.get("tipo") != "Transferência Interna"
        )
        diff = despesas - desp_ant
        sinal = "+" if diff > 0 else ""
        linhas.append(f"- Variação vs mês anterior: {sinal}{_formatar_valor(diff)}")
        linhas.append("")

    # Top 5 categorias
    linhas.extend(
        [
            "## Top 5 Categorias de Gasto",
            "",
            "| Categoria | Valor | % do total |",
            "|-----------|-------|-----------|",
        ]
    )
    for cat, valor in top_categorias:
        pct = (valor / despesas * 100) if despesas > 0 else 0
        linhas.append(f"| {cat} | {_formatar_valor(valor)} | {pct:.1f}% |")
    linhas.append("")

    # Classificação
    linhas.extend(
        [
            "## Por Classificação",
            "",
            f"- Obrigatório: {_formatar_valor(obrigatorio)}",
            f"- Questionável: {_formatar_valor(questionavel)}",
            f"- Supérfluo: {_formatar_valor(superfluo)}",
            "",
        ]
    )

    # Alertas
    linhas.extend(["## Alertas", ""])
    if len(sem_categoria) > 0:
        linhas.append(f"- {len(sem_categoria)} transações sem categoria reconhecida")
    if superfluo > 500:
        linhas.append(f"- Gastos supérfluos acima de R$ 500: {_formatar_valor(superfluo)}")
    if saldo < 0:
        linhas.append(f"- [ALERTA] Saldo negativo no mês: {_formatar_valor(saldo)}")
    if not any("ALERTA" in linha or "transações" in linha for linha in linhas[-3:]):
        linhas.append("- Nenhum alerta crítico")
    linhas.append("")

    # Transferências internas
    total_transf = sum(t["valor"] for t in transferencias)
    linhas.extend(
        [
            "## Transferências Internas",
            "",
            f"- Total movimentado entre contas: {_formatar_valor(total_transf)}",
            f"- Quantidade: {len(transferencias)} transações",
            "",
        ]
    )

    # Transações por pessoa
    gastos_andre = sum(
        t["valor"]
        for t in transacoes_mes
        if t.get("quem") == "André" and t.get("tipo") in ("Despesa", "Imposto")
    )
    gastos_vitoria = sum(
        t["valor"]
        for t in transacoes_mes
        if t.get("quem") == "Vitória" and t.get("tipo") in ("Despesa", "Imposto")
    )
    linhas.extend(
        [
            "## Gastos por Pessoa",
            "",
            f"- André: {_formatar_valor(gastos_andre)}",
            f"- Vitória: {_formatar_valor(gastos_vitoria)}",
            "",
        ]
    )

    secao_metas = _gerar_secao_metas()
    if secao_metas:
        linhas.extend(secao_metas)

    secao_projecao = _gerar_secao_projecao(transacoes, mes_ref)
    if secao_projecao:
        linhas.extend(secao_projecao)

    secao_irpf = _gerar_secao_irpf(transacoes, mes_ref)
    if secao_irpf:
        linhas.extend(secao_irpf)

    linhas.extend(
        [
            "---",
            "",
            f"*Gerado automaticamente em {date.today().isoformat()}*",
        ]
    )

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
