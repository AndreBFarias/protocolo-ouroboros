"""Geração de relatório mensal em Markdown formatado para GitHub."""

from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

from src.load.formatacao_md import (
    barra_progresso_unicode,
    cabecalho_relatorio,
    formatar_valor,
    gerar_mermaid_pie,
    linha_badges,
    secao_colapsavel,
    tabela_categorias,
    tabela_classificacao,
)
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


def _gerar_secao_metas() -> list[str]:
    """Gera seção de metas com barras de progresso Unicode."""
    metas = _carregar_metas()
    if not metas:
        return []

    linhas_tabela: list[str] = [
        "| Meta | Progresso | Prazo |",
        "|:-----|:----------|:------|",
    ]

    for meta in sorted(metas, key=lambda m: m.get("prioridade", 99)):
        nome = meta.get("nome", "Sem nome")
        prazo = meta.get("prazo", "---")
        tipo = meta.get("tipo", "valor")

        if tipo == "binario":
            linhas_tabela.append(f"| {nome} | Pendente | {prazo} |")
        else:
            valor_alvo = meta.get("valor_alvo", 0)
            valor_atual = meta.get("valor_atual", 0)
            progresso = min(valor_atual / valor_alvo, 1.0) if valor_alvo > 0 else 0.0
            barra = barra_progresso_unicode(progresso)
            linhas_tabela.append(f"| {nome} | {barra} | {prazo} |")

    conteudo_detalhado: list[str] = []
    for meta in sorted(metas, key=lambda m: m.get("prioridade", 99)):
        nome = meta.get("nome", "Sem nome")
        nota = meta.get("nota", "")
        deps = meta.get("depende_de", [])
        tipo = meta.get("tipo", "valor")

        detalhes: list[str] = [f"**{nome}**"]
        if tipo != "binario":
            valor_alvo = meta.get("valor_alvo", 0)
            valor_atual = meta.get("valor_atual", 0)
            detalhes.append(f"  {formatar_valor(valor_atual)} / {formatar_valor(valor_alvo)}")
        if nota:
            detalhes.append(f"  *{nota}*")
        if deps:
            detalhes.append(f"  Depende de: {', '.join(deps)}")
        conteudo_detalhado.append("\n".join(detalhes))

    detalhes_md = "\n\n".join(conteudo_detalhado)

    linhas: list[str] = [
        "## Metas",
        "",
        "\n".join(linhas_tabela),
        "",
        secao_colapsavel("Detalhes das metas", detalhes_md),
        "",
    ]

    return linhas


def _gerar_secao_projecao(transacoes: list[dict], mes_ref: str) -> list[str]:
    """Gera seção de projeção usando cálculos unificados do scenarios.py."""
    from src.projections.scenarios import _calcular_medias

    medias = _calcular_medias(transacoes)
    receita_media = medias["receita_media"]
    despesa_media = medias["despesa_media"]
    saldo_medio = medias["saldo_medio"]

    if receita_media == 0.0 and despesa_media == 0.0:
        return []

    projecao_6m = saldo_medio * 6
    projecao_12m = saldo_medio * 12

    linhas: list[str] = [
        "## Projeção",
        "",
        "| Métrica | Valor |",
        "|:--------|------:|",
        f"| Receita média (3 meses) | {formatar_valor(receita_media)} |",
        f"| Despesa média (3 meses) | {formatar_valor(despesa_media)} |",
        f"| Saldo médio mensal | {formatar_valor(saldo_medio)} |",
        f"| Projeção 6 meses | {formatar_valor(projecao_6m)} |",
        f"| Projeção 12 meses | {formatar_valor(projecao_12m)} |",
        "",
    ]

    if saldo_medio > 0:
        linhas.append(
            f"> No ritmo atual, sobram {formatar_valor(projecao_6m)} em 6 meses "
            f"e {formatar_valor(projecao_12m)} em 12 meses."
        )
    else:
        linhas.append(
            f"> **ALERTA:** No ritmo atual, faltam {formatar_valor(abs(projecao_6m))} "
            f"em 6 meses e {formatar_valor(abs(projecao_12m))} em 12 meses."
        )

    linhas.append("")
    return linhas


def _gerar_secao_irpf(transacoes: list[dict], mes_ref: str) -> list[str]:
    """Gera seção de IRPF acumulado no ano (colapsável)."""
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

    conteudo = (
        f"| Métrica | Valor |\n"
        f"|:--------|------:|\n"
        f"| Rendimentos tributáveis | {formatar_valor(rendimentos_tributaveis)} |\n"
        f"| Despesas dedutíveis (saúde) | {formatar_valor(despesas_dedutiveis)} |\n"
        f"| Impostos pagos (DARF/DAS) | {formatar_valor(impostos_pagos)} |"
    )

    return [
        secao_colapsavel(f"IRPF Acumulado ({ano})", conteudo),
        "",
    ]


def gerar_relatorio_mes(
    transacoes: list[dict],
    mes_ref: str,
    transacoes_mes_anterior: Optional[list[dict]] = None,
) -> str:
    """Gera o relatório markdown de um mês específico."""
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
    poupanca = (saldo / receitas * 100) if receitas > 0 else 0.0

    gastos_categoria: dict[str, float] = {}
    classificacao_categoria: dict[str, str] = {}
    for t in transacoes_mes:
        if t.get("tipo") in ("Despesa", "Imposto"):
            cat = t.get("categoria", "Outros")
            gastos_categoria[cat] = gastos_categoria.get(cat, 0) + t["valor"]
            if cat not in classificacao_categoria:
                classificacao_categoria[cat] = t.get("classificacao", "N/A")

    top_categorias = sorted(gastos_categoria.items(), key=lambda x: x[1], reverse=True)[:10]

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

    sem_categoria = [t for t in transacoes_mes if t.get("categoria") == "Outros"]

    # -- Montar relatório --

    linhas: list[str] = []

    # Header com logo e badges
    linhas.append(cabecalho_relatorio(mes_ref))
    linhas.append("")
    linhas.append(linha_badges(receitas, despesas, saldo, poupanca))
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    # Resumo em tabela
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append("| Métrica | Valor |")
    linhas.append("|:--------|------:|")
    linhas.append(f"| Receita total | {formatar_valor(receitas)} |")
    linhas.append(f"| Despesa total | {formatar_valor(despesas)} |")
    linhas.append(f"| Saldo | {formatar_valor(saldo)} |")
    linhas.append(f"| Taxa de poupança | {poupanca:.1f}% |")

    if transacoes_mes_anterior:
        desp_ant = sum(
            t["valor"]
            for t in transacoes_mes_anterior
            if t.get("tipo") in ("Despesa", "Imposto") and t.get("tipo") != "Transferência Interna"
        )
        diff = despesas - desp_ant
        sinal = "+" if diff > 0 else ""
        linhas.append(f"| vs mês anterior | {sinal}{formatar_valor(diff)} |")

    linhas.append("")

    # Mermaid pie chart
    if gastos_categoria:
        linhas.append("## Categorias")
        linhas.append("")
        linhas.append(gerar_mermaid_pie(gastos_categoria))
        linhas.append("")

        # Top 10 colapsável
        dados_tabela = [
            (cat, valor, (valor / despesas * 100) if despesas > 0 else 0.0,
             classificacao_categoria.get(cat, "N/A"))
            for cat, valor in top_categorias
        ]
        conteudo_top10 = tabela_categorias(dados_tabela)
        linhas.append(secao_colapsavel("Top 10 Categorias", conteudo_top10))
        linhas.append("")

    # Classificação
    linhas.append("## Classificação")
    linhas.append("")
    linhas.append(tabela_classificacao(obrigatorio, questionavel, superfluo))
    linhas.append("")

    # Gastos por pessoa
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

    conteudo_pessoa = (
        "| Pessoa | Valor |\n"
        "|:-------|------:|\n"
        f"| André | {formatar_valor(gastos_andre)} |\n"
        f"| Vitória | {formatar_valor(gastos_vitoria)} |"
    )
    linhas.append(secao_colapsavel("Gastos por Pessoa", conteudo_pessoa))
    linhas.append("")

    # Transferências internas
    total_transf = sum(t["valor"] for t in transferencias)
    if transferencias:
        conteudo_transf = (
            f"- Total movimentado entre contas: {formatar_valor(total_transf)}\n"
            f"- Quantidade: {len(transferencias)} transações"
        )
        linhas.append(secao_colapsavel("Transferências Internas", conteudo_transf))
        linhas.append("")

    # Alertas
    alertas: list[str] = []
    if len(sem_categoria) > 0:
        alertas.append(f"- {len(sem_categoria)} transações sem categoria reconhecida")
    if superfluo > 500:
        alertas.append(f"- Gastos supérfluos acima de R$ 500: {formatar_valor(superfluo)}")
    if saldo < 0:
        alertas.append(f"- **ALERTA:** Saldo negativo no mês: {formatar_valor(saldo)}")

    if alertas:
        linhas.append("## Alertas")
        linhas.append("")
        linhas.extend(alertas)
        linhas.append("")

    # Metas
    secao_metas = _gerar_secao_metas()
    if secao_metas:
        linhas.extend(secao_metas)

    # Projeção
    secao_projecao = _gerar_secao_projecao(transacoes, mes_ref)
    if secao_projecao:
        linhas.extend(secao_projecao)

    # IRPF
    secao_irpf = _gerar_secao_irpf(transacoes, mes_ref)
    if secao_irpf:
        linhas.extend(secao_irpf)

    # Footer
    linhas.extend([
        "---",
        "",
        '<div align="center">',
        "",
        f"*Gerado automaticamente em {date.today().isoformat()}*",
        "",
        "</div>",
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
