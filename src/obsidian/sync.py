"""Sincronização de relatórios financeiros com o vault Obsidian."""

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
    """Formata valor monetário no padrão brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


SIGLAS_PRESERVAR: set[str] = {"PF", "PJ", "CNH", "IRPF", "PIX", "INSS", "IRRF", "CLT", "MEI", "DAS"}
PREPOSICOES_PT: set[str] = {"de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas"}


def _formatar_nome(nome: str) -> str:
    """Aplica title case preservando siglas (PF, PJ) e preposições (de, da)."""
    palavras = nome.title().split()
    resultado: list[str] = []
    for i, palavra in enumerate(palavras):
        limpa = palavra.strip("()+")
        if limpa.upper() in SIGLAS_PRESERVAR:
            prefixo = "(" if palavra.startswith("(") else ""
            sufixo = ")" if palavra.endswith(")") else ""
            resultado.append(f"{prefixo}{limpa.upper()}{sufixo}")
        elif i > 0 and limpa.lower() in PREPOSICOES_PT:
            resultado.append(palavra.lower())
        else:
            resultado.append(palavra)
    return " ".join(resultado)


MESES_PT: dict[str, str] = {
    "01": "Janeiro",
    "02": "Fevereiro",
    "03": "Março",
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
    """Extrai receita, despesa e saldo do conteúdo do relatório."""
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
                logger.warning("Valor inválido para %s: %s", chave, match.group(1))

    return valores


def _nome_mes_pt(mes_ref: str) -> str:
    """Retorna o nome do mês em português a partir de YYYY-MM."""
    partes = mes_ref.split("-")
    if len(partes) != 2:
        return mes_ref
    numero_mes = partes[1]
    return MESES_PT.get(numero_mes, mes_ref)


def _extrair_created_existente(caminho: Path) -> Optional[str]:
    """Extrai o campo created do frontmatter de um arquivo existente."""
    if not caminho.exists():
        return None
    try:
        conteudo = caminho.read_text(encoding="utf-8")
        match = re.search(r'^created:\s*"?(\d{4}-\d{2}-\d{2})"?', conteudo, re.MULTILINE)
        if match:
            return match.group(1)
    except Exception as err:
        logger.warning("Erro ao ler created de %s: %s", caminho, err)
    return None


def _gerar_frontmatter(
    mes_ref: str,
    valores: dict[str, Optional[float]],
    created_existente: Optional[str] = None,
) -> str:
    """Gera o frontmatter YAML para um relatório mensal."""
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

    frontmatter_dict["tags"] = ["financeiro", "mensal", "relatório"]
    frontmatter_dict["aliases"] = [
        f"Relatório {nome_mes} {ano}",
        f"Ouroboros {nome_mes}",
    ]
    frontmatter_dict["created"] = created_existente or date.today().isoformat()

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
    """Gera seção de backlinks para metas financeiras."""
    linhas = ["", "## Links"]
    for meta in metas:
        nome = str(meta.get("nome", ""))
        nome_formatado = _formatar_nome(nome)
        linhas.append(f"- [[{nome_formatado}]]")
    return "\n".join(linhas)


def _remover_linha_gerado(conteudo: str) -> str:
    """Remove a linha de 'Gerado automaticamente' do conteúdo original."""
    linhas = conteudo.split("\n")
    linhas_filtradas = [
        linha for linha in linhas if not linha.strip().startswith("*Gerado automaticamente")
    ]
    return "\n".join(linhas_filtradas).rstrip()


def _carregar_metas() -> list[dict[str, object]]:
    """Carrega metas do arquivo YAML."""
    if not METAS_YAML.exists():
        logger.warning("Arquivo de metas não encontrado: %s", METAS_YAML)
        return []

    with METAS_YAML.open("r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)

    return dados.get("metas", []) if dados else []


def sincronizar_relatorios(diretorio_output: Path) -> list[Path]:
    """Copia relatórios MD do pipeline para o vault Obsidian.

    Para cada relatório YYYY-MM_relatorio.md:
    1. Adiciona frontmatter YAML (tags, tipo, aliases, datas)
    2. Adiciona backlinks para metas e dívidas
    3. Copia para VAULT/Pessoal/Financeiro/Relatorios/YYYY-MM.md
    """
    RELATORIOS_PATH.mkdir(parents=True, exist_ok=True)

    metas = _carregar_metas()
    arquivos_relatorio = sorted(diretorio_output.glob("*_relatorio.md"))

    if not arquivos_relatorio:
        logger.warning("Nenhum relatório encontrado em %s", diretorio_output)
        return []

    copiados: list[Path] = []

    for arquivo in arquivos_relatorio:
        mes_ref = arquivo.stem.replace("_relatorio", "")
        conteudo_original = arquivo.read_text(encoding="utf-8")

        destino = RELATORIOS_PATH / f"{mes_ref}.md"
        created_existente = _extrair_created_existente(destino)

        valores = _extrair_valores_relatorio(conteudo_original)
        frontmatter = _gerar_frontmatter(mes_ref, valores, created_existente)
        conteudo_limpo = _remover_linha_gerado(conteudo_original)
        backlinks = _gerar_backlinks(metas)

        conteudo_final = f"{frontmatter}\n\n{conteudo_limpo}\n{backlinks}\n"

        destino.write_text(conteudo_final, encoding="utf-8")
        copiados.append(destino)

    logger.info(
        "Relatórios sincronizados: %d arquivos em %s",
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

        nome_arquivo = _formatar_nome(nome)

        frontmatter_linhas = [
            "---",
            "tipo: meta_financeira",
            f'nome: "{nome}"',
        ]

        if tipo_meta != "binario":
            frontmatter_linhas.append(f"valor_alvo: {valor_alvo}")
            frontmatter_linhas.append(f"valor_atual: {valor_atual}")

        frontmatter_linhas.extend(
            [
                f"prioridade: {prioridade}",
                f'prazo: "{prazo}"',
                'tags: ["financeiro", "meta"]',
                "---",
            ]
        )

        corpo_linhas = [
            "",
            f"# {_formatar_nome(nome)}",
            "",
        ]

        if tipo_meta == "binario":
            corpo_linhas.append("Tipo: Meta binária (sim/não)")
            corpo_linhas.append(f"Prazo: {prazo}")
        else:
            valor_alvo_fmt = _formatar_moeda(valor_alvo)
            progresso = (valor_atual / valor_alvo * 100) if valor_alvo > 0 else 0
            corpo_linhas.append(f"Valor alvo: {valor_alvo_fmt}")
            corpo_linhas.append(f"Progresso: {progresso:.0f}%")

        if nota:
            corpo_linhas.extend(["", f"Nota: {nota}"])

        if depende_de:
            corpo_linhas.extend(["", "### Dependências"])
            for dep in depende_de:
                corpo_linhas.append(f"- {dep}")

        corpo_linhas.extend(
            [
                "",
                "## Relatórios relacionados",
                "",
                "```dataview",
                "LIST",
                'FROM "Pessoal/Financeiro/Relatorios"',
                "SORT file.name DESC",
                "LIMIT 6",
                "```",
            ]
        )

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

## Relatórios Recentes

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

## Navegação

- [[Pessoal/Financeiro/Relatorios|Todos os Relatórios]]
- [[Pessoal/Financeiro/Metas|Todas as Metas]]
"""

    destino = FINANCEIRO_PATH / "Dashboard Financeiro.md"
    destino.write_text(conteudo, encoding="utf-8")
    logger.info("MOC financeiro criado: %s", destino)
    return destino


def executar_sincronizacao() -> None:
    """Executa o fluxo completo de sincronização com o vault Obsidian."""
    logger.info("Iniciando sincronização com vault Obsidian")
    logger.info("Vault: %s", VAULT_PATH)
    logger.info("Output: %s", OUTPUT_PATH)

    if not VAULT_PATH.exists():
        logger.error("Vault Obsidian não encontrado em %s", VAULT_PATH)
        return

    if not OUTPUT_PATH.exists():
        logger.error("Diretório de output não encontrado em %s", OUTPUT_PATH)
        return

    relatorios = sincronizar_relatorios(OUTPUT_PATH)
    logger.info("Relatórios sincronizados: %d", len(relatorios))

    metas = criar_notas_metas()
    logger.info("Notas de metas criadas: %d", len(metas))

    moc = criar_moc_financeiro()
    logger.info("MOC criado: %s", moc)

    logger.info("Sincronização concluída com sucesso")


def gerar_moc_mensal(mes_ref: str, caminho_grafo: Optional[Path] = None) -> str:
    """Gera Markdown do MOC (Map of Content) mensal com wikilinks.

    Lê o grafo SQLite read-only e monta nota com:
    - Frontmatter YAML (tipo, mes, tags, aliases, created, atualizado,
      agregados receita/despesa/saldo, contagem de documentos).
    - Corpo com wikilinks `[[transacao_ID]]`, `[[documento_CHAVE]]`,
      `[[fornecedor_NOME]]`.
    - Seção de top fornecedores, top categorias, alertas.
    - Linha final "Gerado automaticamente por src/obsidian/sync.py."

    Se grafo ausente ou mês sem dados, retorna MOC mínimo marcado como
    "(sem dados)". Nunca levanta exceção.

    Args:
        mes_ref: formato YYYY-MM.
        caminho_grafo: path do SQLite; default=src/dashboard/dados.CAMINHO_GRAFO.

    Returns:
        String Markdown pronta para gravar como `.md`.
    """
    import sqlite3

    if caminho_grafo is None:
        from src.dashboard.dados import CAMINHO_GRAFO as _CAMINHO
        caminho_grafo = _CAMINHO

    nome_mes = _nome_mes_pt(mes_ref)
    ano = mes_ref.split("-")[0] if "-" in mes_ref else mes_ref

    if not caminho_grafo.exists():
        return _moc_fallback(mes_ref, nome_mes, ano)

    import json as _json

    conn = sqlite3.connect(f"file:{caminho_grafo}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # encontra node período do mês
        row_per = conn.execute(
            "SELECT id FROM node WHERE tipo = 'periodo' AND nome_canonico = ?",
            (mes_ref,),
        ).fetchone()

        transacoes: list[dict] = []
        documentos: list[dict] = []
        fornecedores_agg: dict[int, dict] = {}

        if row_per is not None:
            periodo_id = int(row_per["id"])
            # transações do mês (via ocorre_em)
            for edge_row in conn.execute(
                "SELECT src_id FROM edge WHERE dst_id = ? AND tipo = 'ocorre_em'",
                (periodo_id,),
            ):
                node_row = conn.execute(
                    "SELECT id, tipo, nome_canonico, metadata FROM node WHERE id = ?",
                    (int(edge_row["src_id"]),),
                ).fetchone()
                if not node_row:
                    continue
                try:
                    meta_tx = _json.loads(node_row["metadata"] or "{}")
                except (_json.JSONDecodeError, TypeError):
                    meta_tx = {}
                if node_row["tipo"] == "transacao":
                    transacoes.append(
                        {
                            "id": int(node_row["id"]),
                            "nome": node_row["nome_canonico"],
                            "valor": float(meta_tx.get("valor", 0.0) or 0.0),
                            "tipo_tx": meta_tx.get("tipo", ""),
                            "local": meta_tx.get("local", ""),
                        }
                    )
                elif node_row["tipo"] == "documento":
                    documentos.append(
                        {
                            "id": int(node_row["id"]),
                            "nome": node_row["nome_canonico"],
                            "tipo_doc": meta_tx.get("tipo_documento", "documento"),
                            "total": float(meta_tx.get("total", 0.0) or 0.0),
                        }
                    )

            # fornecedores agregados (via fornecido_por a partir dos documentos)
            for doc in documentos:
                for e_row in conn.execute(
                    "SELECT dst_id FROM edge WHERE src_id = ? AND tipo = 'fornecido_por'",
                    (doc["id"],),
                ):
                    fid = int(e_row["dst_id"])
                    slot = fornecedores_agg.setdefault(
                        fid, {"id": fid, "nome": "", "total": 0.0, "docs": 0}
                    )
                    slot["total"] += doc["total"]
                    slot["docs"] += 1

            for fid, slot in list(fornecedores_agg.items()):
                node_row = conn.execute(
                    "SELECT nome_canonico FROM node WHERE id = ?", (fid,)
                ).fetchone()
                slot["nome"] = node_row["nome_canonico"] if node_row else str(fid)
    finally:
        conn.close()

    receita_total = sum(
        abs(t["valor"]) for t in transacoes if t["tipo_tx"] == "Receita"
    )
    despesa_total = sum(
        abs(t["valor"])
        for t in transacoes
        if t["tipo_tx"] in ("Despesa", "Imposto")
    )
    saldo = receita_total - despesa_total

    linhas: list[str] = ["---"]
    linhas.append("tipo: moc")
    linhas.append(f'mes: "{mes_ref}"')
    linhas.append("aliases:")
    linhas.append(f'  - "MOC {nome_mes} {ano}"')
    linhas.append(f'  - "{mes_ref}"')
    linhas.append("tags:")
    linhas.append("  - moc")
    linhas.append("  - financeiro")
    linhas.append("  - mensal")
    linhas.append(f'criado: "{date.today().isoformat()}"')
    linhas.append(f'atualizado: "{date.today().isoformat()}"')
    linhas.append(f"receita_total: {receita_total:.2f}")
    linhas.append(f"despesa_total: {despesa_total:.2f}")
    linhas.append(f"saldo: {saldo:.2f}")
    linhas.append(f"documentos: {len(documentos)}")
    linhas.append("---")
    linhas.append("")
    linhas.append(f"# MOC -- {nome_mes} {ano}")
    linhas.append("")
    linhas.append("## Saldo do mês")
    linhas.append("")
    linhas.append(f"- **Receita:** {_formatar_moeda(receita_total)}")
    linhas.append(f"- **Despesa:** {_formatar_moeda(despesa_total)}")
    linhas.append(f"- **Saldo:** {_formatar_moeda(saldo)}")
    linhas.append("")
    linhas.append(f"## Documentos ({len(documentos)})")
    linhas.append("")
    for doc in documentos[:20]:
        linhas.append(
            f"- [[documento_{doc['id']}|{doc['nome']}]] "
            f"({doc['tipo_doc']}) -- {_formatar_moeda(doc['total'])}"
        )
    if not documentos:
        linhas.append("_(nenhum documento registrado neste mês)_")
    linhas.append("")

    top_fornecedores = sorted(
        fornecedores_agg.values(), key=lambda x: x["total"], reverse=True
    )[:10]
    linhas.append("## Top fornecedores")
    linhas.append("")
    for forn in top_fornecedores:
        linhas.append(
            f"- [[fornecedor_{forn['id']}|{forn['nome']}]] -- "
            f"{_formatar_moeda(forn['total'])} ({forn['docs']} docs)"
        )
    if not top_fornecedores:
        linhas.append("_(sem fornecedores registrados)_")
    linhas.append("")

    linhas.append(f"## Transações ({len(transacoes)})")
    linhas.append("")
    for tx in transacoes[:30]:
        rotulo = tx["local"] or tx["nome"]
        linhas.append(
            f"- [[transacao_{tx['id']}|{rotulo}]] -- "
            f"{_formatar_moeda(abs(tx['valor']))}"
        )
    if not transacoes:
        linhas.append("_(nenhuma transação registrada)_")
    linhas.append("")

    linhas.append("## Conexões")
    linhas.append("")
    linhas.append(f"- [[MOC_{_mes_anterior(mes_ref)}]] (anterior)")
    linhas.append(f"- [[MOC_{_mes_seguinte(mes_ref)}]] (próximo)")
    linhas.append(f"- [[Relatorio_{mes_ref}]]")
    linhas.append("")
    linhas.append("---")
    linhas.append("")
    linhas.append("*Gerado automaticamente por src/obsidian/sync.py. Não editar.*")

    return "\n".join(linhas) + "\n"


def _moc_fallback(mes_ref: str, nome_mes: str, ano: str) -> str:
    """MOC mínimo quando grafo ausente (ADR-10)."""
    return (
        f"---\n"
        f"tipo: moc\n"
        f'mes: "{mes_ref}"\n'
        f"tags: [moc, financeiro]\n"
        f'criado: "{date.today().isoformat()}"\n'
        f"---\n\n"
        f"# MOC -- {nome_mes} {ano}\n\n"
        f"_(sem dados -- grafo ainda não populado)_\n\n"
        f"*Gerado automaticamente por src/obsidian/sync.py. Não editar.*\n"
    )


def _mes_anterior(mes_ref: str) -> str:
    """Retorna mês anterior em YYYY-MM (simples, sem validação agressiva)."""
    try:
        ano_s, mes_s = mes_ref.split("-")
        ano_i = int(ano_s)
        mes_i = int(mes_s)
        if mes_i <= 1:
            return f"{ano_i - 1}-12"
        return f"{ano_i}-{mes_i - 1:02d}"
    except (ValueError, AttributeError):
        return mes_ref


def _mes_seguinte(mes_ref: str) -> str:
    """Retorna mês seguinte em YYYY-MM."""
    try:
        ano_s, mes_s = mes_ref.split("-")
        ano_i = int(ano_s)
        mes_i = int(mes_s)
        if mes_i >= 12:
            return f"{ano_i + 1}-01"
        return f"{ano_i}-{mes_i + 1:02d}"
    except (ValueError, AttributeError):
        return mes_ref


if __name__ == "__main__":
    executar_sincronizacao()


# "Não é porque as coisas são difíceis que não ousamos;
# é porque não ousamos que são difíceis." -- Sêneca
