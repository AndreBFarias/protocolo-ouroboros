"""Funções de formatação Markdown para relatórios GitHub-ready."""

from __future__ import annotations

from urllib.parse import quote

DRACULA = {
    "positivo": "50FA7B",
    "negativo": "FF5555",
    "destaque": "BD93F9",
    "neutro": "8BE9FD",
    "alerta": "FFB86C",
    "rosa": "FF79C6",
    "texto": "F8F8F2",
    "comentario": "6272A4",
}


def callout_github(tipo: str, conteudo: str) -> str:
    """Gera callout nativo do GitHub (NOTE, WARNING, TIP, IMPORTANT, CAUTION)."""
    linhas_conteudo = conteudo.strip().split("\n")
    corpo = "\n> ".join(linhas_conteudo)
    return f"> [!{tipo.upper()}]\n> {corpo}"


def separador_secao() -> str:
    """Retorna separador horizontal para Markdown."""
    return "\n---\n"


def formatar_valor(valor: float) -> str:
    """Formata valor monetário no padrão brasileiro."""
    sinal = "-" if valor < 0 else ""
    valor_abs = abs(valor)
    return f"{sinal}R$ {valor_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_badge(label: str, valor: str, cor_hex: str) -> str:
    """Gera badge shields.io com label, valor e cor Dracula."""
    label_enc = quote(label, safe="")
    valor_enc = quote(valor.replace("-", "neg "), safe="")
    return (
        f"![{label}](https://img.shields.io/badge/"
        f"{label_enc}-{valor_enc}-{cor_hex}?style=flat-square)"
    )


def gerar_mermaid_pie(categorias: dict[str, float], titulo: str = "Gastos por Categoria") -> str:
    """Gera bloco Mermaid pie chart com top 5 categorias."""
    if not categorias:
        return ""

    ordenadas = sorted(categorias.items(), key=lambda x: x[1], reverse=True)
    top5 = ordenadas[:5]
    resto = sum(v for _, v in ordenadas[5:])

    linhas = ["```mermaid", f"pie title {titulo}"]

    for cat, valor in top5:
        linhas.append(f'    "{cat}" : {int(valor)}')

    if resto > 0:
        linhas.append(f'    "Outros" : {int(resto)}')

    linhas.append("```")
    return "\n".join(linhas)


def barra_progresso_unicode(progresso: float, largura: int = 10) -> str:
    """Gera barra de progresso Unicode. Progresso de 0.0 a 1.0."""
    progresso = max(0.0, min(1.0, progresso))
    preenchido = int(progresso * largura)
    vazio = largura - preenchido
    return f"{'█' * preenchido}{'░' * vazio} {progresso * 100:.0f}%"


def secao_colapsavel(titulo: str, conteudo: str) -> str:
    """Gera seção colapsável HTML com <details>."""
    return f"<details>\n<summary>{titulo}</summary>\n\n{conteudo}\n</details>"


def cabecalho_relatorio(mes_ref: str, logo_path: str = "../../assets/icon.png") -> str:
    """Gera cabeçalho centralizado com logo para relatório."""
    return (
        f'<div align="center">\n\n'
        f'<img src="{logo_path}" width="80" alt="Protocolo Ouroboros">\n\n'
        f"# Relatório Financeiro -- {mes_ref}\n\n"
        f"</div>"
    )


def linha_badges(receita: float, despesa: float, saldo: float, poupanca: float) -> str:
    """Gera badges com métricas principais em grade 2x2 para legibilidade."""
    cor_saldo = DRACULA["positivo"] if saldo >= 0 else DRACULA["negativo"]
    cor_poupanca = (
        DRACULA["neutro"]
        if poupanca > 10
        else (DRACULA["alerta"] if poupanca > 0 else DRACULA["negativo"])
    )

    badges = [
        gerar_badge("Receita", formatar_valor(receita), DRACULA["positivo"]),
        gerar_badge("Despesa", formatar_valor(despesa), DRACULA["negativo"]),
        gerar_badge("Saldo", formatar_valor(saldo), cor_saldo),
        gerar_badge("Poupança", f"{poupanca:.1f}%", cor_poupanca),
    ]

    return f'<div align="center">\n\n{badges[0]} {badges[1]}<br>\n{badges[2]} {badges[3]}\n\n</div>'


def tabela_categorias(
    categorias: list[tuple[str, float, float, str]],
) -> str:
    """Gera tabela de categorias com ranking.

    Cada item: (categoria, valor, percentual, classificação).
    """
    linhas = [
        "| # | Categoria | Valor | % | Classificação |",
        "|--:|:----------|------:|--:|:--------------|",
    ]
    for i, (cat, valor, pct, classif) in enumerate(categorias, 1):
        linhas.append(f"| {i} | {cat} | {formatar_valor(valor)} | {pct:.1f}% | {classif} |")

    return "\n".join(linhas)


def tabela_classificacao(obrigatorio: float, questionavel: float, superfluo: float) -> str:
    """Gera tabela de classificação com percentuais."""
    total = obrigatorio + questionavel + superfluo
    if total == 0:
        return ""

    def pct(v: float) -> float:
        return (v / total * 100) if total > 0 else 0.0

    linhas = [
        "| Tipo | Valor | % |",
        "|:-----|------:|--:|",
        f"| Obrigatório | {formatar_valor(obrigatorio)} | {pct(obrigatorio):.1f}% |",
        f"| Questionável | {formatar_valor(questionavel)} | {pct(questionavel):.1f}% |",
        f"| Supérfluo | {formatar_valor(superfluo)} | {pct(superfluo):.1f}% |",
    ]

    return "\n".join(linhas)


# "A beleza das coisas existe no espírito de quem as contempla." -- David Hume
