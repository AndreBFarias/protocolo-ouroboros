"""Painel lateral de drill-down item -- INFRA-DRILL-DOWN-ITEM.

Resolve a pergunta canônica "gastei R$ X na DROGASIL, quais remédios
comprei?". Recebe a transação (linha do DataFrame extrato) + documento
vinculado + lista de itens do grafo e devolve o HTML do painel lateral.

A função pública ``renderizar_painel_drill_down`` é pura: não acessa
``st.session_state``, não lê arquivos. Quem chama (página extrato)
busca os dados via ``src.graph.drill_down`` e injeta com
``st.markdown(..., unsafe_allow_html=True)``.

Blocos do painel
-----------------
1. Header: data, valor, fornecedor, conta, sha8 da transação.
2. Documento vinculado: sha8 + tipo_documento + data_emissao + link.
3. Itens da NF/cupom: tabela ``codigo | descricao | qtd | unit | total``.  # noqa: accent
4. Cruzamentos (opcional): outras transações com itens iguais
   (mesmo ``produto_canonico``).
5. Sem vínculo: callout "sem documento vinculado" + botão placeholder.

Persistência opcional
---------------------
``persistir_revisao(transacao_id)`` faz best-effort em
``data/output/revisao_humana.sqlite``: cria a tabela se não existir,
insere ``(transacao_id, marcado_em)``. Quando o arquivo .sqlite não
existe, é no-op silencioso (graceful degradation -- ADR-10).

Por que existe (relação com drawer_transacao.py)
-------------------------------------------------
``drawer_transacao.py`` (UX-RD-06) é o drawer do *Streamlit* via
selectbox -- mostra JSON da transação + stub de doc vinculado.
``painel_drill_down.py`` é o painel acionado por *query-param*
``?transacao_id=<int>`` que mostra os ITENS do documento (walk de 2
saltos do grafo). Coexistência por escopo distinto: drawer = inspeção
JSON; painel = drill-down semântico até item granular.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.dashboard.componentes.html_utils import minificar

# ---------------------------------------------------------------------------
# Helpers de formatação
# ---------------------------------------------------------------------------


def _formatar_brl(valor: float) -> str:
    """Formato monetário PT-BR (vírgula decimal, ponto milhar)."""
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _escape(texto: str) -> str:
    """Escape HTML mínimo para evitar quebra de tags."""
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _sha8_de(valor: Any) -> str:
    """Devolve os primeiros 8 caracteres de um sha256 ou identificador.

    Tolerante a None / NaN / valores curtos: nunca levanta exceção e
    nunca devolve string com mais de 8 caracteres.
    """
    if valor is None:
        return "-"
    try:
        if pd.isna(valor):  # type: ignore[arg-type]
            return "-"
    except (TypeError, ValueError):
        pass  # noqa: BLE001 -- pd.isna não aceita certos tipos; fallback abaixo
    s = str(valor).strip()
    if not s:
        return "-"
    return s[:8]


# ---------------------------------------------------------------------------
# Blocos de HTML
# ---------------------------------------------------------------------------


def _header_html(transacao: dict[str, Any]) -> str:
    """Bloco do cabeçalho: data, valor, fornecedor, conta, sha8."""
    data = _escape(str(transacao.get("data") or "-")[:10])
    try:
        valor_num = float(transacao.get("valor") or 0.0)
    except (TypeError, ValueError):
        valor_num = 0.0
    valor_str = _formatar_brl(valor_num)
    fornecedor = _escape(transacao.get("local") or transacao.get("fornecedor") or "-")
    conta = _escape(transacao.get("banco_origem") or transacao.get("conta") or "-")
    sha8 = _escape(_sha8_de(transacao.get("identificador") or transacao.get("sha256")))

    cor_valor = "var(--accent-red)" if valor_num < 0 else "var(--d7-graduado)"

    return minificar(
        f"""
        <div class="painel-drill-header">
            <div class="painel-drill-titulo">
                <span class="painel-drill-rotulo">DRILL-DOWN · TRANSAÇÃO</span>
                <code class="painel-drill-sha8">{sha8}</code>
            </div>
            <div class="painel-drill-meta">
                <div class="painel-drill-meta-item">
                    <span class="k">data</span>
                    <span class="v">{data}</span>
                </div>
                <div class="painel-drill-meta-item">
                    <span class="k">valor</span>
                    <span class="v" style="color:{cor_valor};">{valor_str}</span>
                </div>
                <div class="painel-drill-meta-item">
                    <span class="k">fornecedor</span>
                    <span class="v">{fornecedor}</span>
                </div>
                <div class="painel-drill-meta-item">
                    <span class="k">conta</span>
                    <span class="v">{conta}</span>
                </div>
            </div>
        </div>
        """
    )


def _documento_vinculado_html(documento: dict[str, Any] | None) -> str:
    """Bloco "Documento vinculado". Quando ausente, devolve string vazia.

    A renderização do "sem vínculo" é responsabilidade de
    ``_sem_vinculo_html`` para manter blocos coesos.
    """
    if not documento:
        return ""
    sha8 = _escape(_sha8_de(documento.get("nome_canonico") or documento.get("sha256")))
    tipo_doc = _escape(documento.get("tipo_documento") or "-")
    data_emissao = _escape(str(documento.get("data_emissao") or "-")[:10])
    razao_social = _escape(documento.get("razao_social") or "-")
    arquivo_origem = _escape(documento.get("arquivo_origem") or "")

    arquivo_html = ""
    if arquivo_origem:
        arquivo_html = (
            f'<div class="painel-drill-doc-arquivo">'
            f'<span class="k">arquivo</span>'
            f'<code class="v">{arquivo_origem}</code>'
            f"</div>"
        )

    return minificar(
        f"""
        <div class="painel-drill-bloco">
            <span class="painel-drill-bloco-titulo">DOCUMENTO VINCULADO</span>
            <div class="painel-drill-doc-grid">
                <div><span class="k">sha8</span><code class="v syn-number">{sha8}</code></div>
                <div><span class="k">tipo</span><span class="v syn-string">{tipo_doc}</span></div>
                <div><span class="k">emissão</span><span class="v">{data_emissao}</span></div>
                <div><span class="k">emitente</span><span class="v">{razao_social}</span></div>
            </div>
            {arquivo_html}
        </div>
        """
    )


def _formatar_qtd(valor: Any) -> str:
    """Quantidade com até 3 casas, suprimindo zeros à direita."""
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return "-"
    if n == 0:
        return "0"
    s = f"{n:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _itens_html(itens: list[dict[str, Any]]) -> str:
    """Tabela de itens granulares do documento.

    Cada item é dict com chaves opcionais: ``codigo`` (str), ``descricao``  # noqa: accent
    (str), ``quantidade`` ou ``qtde`` (float), ``valor_unitario`` (float),
    ``valor_total`` (float).
    """
    if not itens:
        return minificar(
            """
            <div class="painel-drill-bloco">
                <span class="painel-drill-bloco-titulo">ITENS</span>
                <p class="painel-drill-vazio">
                    Documento vinculado não tem itens granulares
                    (ex: holerite, DAS, fatura sem detalhamento).
                </p>
            </div>
            """
        )

    linhas: list[str] = []
    for it in itens:
        codigo = _escape(str(it.get("codigo") or it.get("ean") or "-"))
        descricao = _escape(str(it.get("descricao") or it.get("nome") or "-"))
        if len(descricao) > 60:
            descricao = descricao[:57] + "..."
        qtd = _escape(_formatar_qtd(it.get("quantidade") or it.get("qtde") or 0))
        unit = it.get("valor_unitario")
        total = it.get("valor_total")
        try:
            unit_str = _formatar_brl(float(unit)) if unit is not None else "-"
        except (TypeError, ValueError):
            unit_str = "-"
        try:
            total_str = _formatar_brl(float(total)) if total is not None else "-"
        except (TypeError, ValueError):
            total_str = "-"
        linhas.append(
            f'<tr>'
            f'<td class="col-mono">{codigo}</td>'
            f"<td>{descricao}</td>"
            f'<td class="col-num">{qtd}</td>'
            f'<td class="col-num">{unit_str}</td>'
            f'<td class="col-num">{total_str}</td>'
            f"</tr>"
        )

    cabecalho = (
        "<thead><tr>"
        "<th>Código</th>"
        "<th>Descrição</th>"
        '<th class="col-num">Qtd</th>'
        '<th class="col-num">Unit</th>'
        '<th class="col-num">Total</th>'
        "</tr></thead>"
    )
    return minificar(
        '<div class="painel-drill-bloco">'
        '<span class="painel-drill-bloco-titulo">ITENS</span>'
        '<div class="painel-drill-itens-wrap">'
        f'<table class="painel-drill-itens">{cabecalho}'
        f'<tbody>{"".join(linhas)}</tbody>'
        "</table>"
        "</div>"
        "</div>"
    )


def _cruzamentos_html(cruzamentos: list[dict[str, Any]]) -> str:
    """Bloco opcional "Cruzamentos": outras transações com itens iguais.

    Cada entrada é dict {data, local, valor, sha8_transacao,
    produto_canonico}. Lista vazia => bloco não renderizado.
    """
    if not cruzamentos:
        return ""
    linhas: list[str] = []
    for c in cruzamentos:
        data = _escape(str(c.get("data") or "-")[:10])
        local = _escape(str(c.get("local") or "-"))
        try:
            valor_num = float(c.get("valor") or 0.0)
        except (TypeError, ValueError):
            valor_num = 0.0
        valor_str = _formatar_brl(valor_num)
        sha8 = _escape(_sha8_de(c.get("sha8_transacao") or c.get("sha256")))
        produto = _escape(str(c.get("produto_canonico") or "-"))
        linhas.append(
            f"<tr>"
            f'<td class="col-mono">{data}</td>'
            f"<td>{local}</td>"
            f'<td class="col-num">{valor_str}</td>'
            f'<td class="col-mono">{sha8}</td>'
            f"<td>{produto}</td>"
            f"</tr>"
        )
    cabecalho = (
        "<thead><tr>"
        "<th>Data</th>"
        "<th>Local</th>"
        '<th class="col-num">Valor</th>'
        "<th>sha8 tx</th>"
        "<th>Produto canônico</th>"
        "</tr></thead>"
    )
    return minificar(
        '<div class="painel-drill-bloco">'
        '<span class="painel-drill-bloco-titulo">CRUZAMENTOS · MESMO ITEM</span>'
        '<div class="painel-drill-itens-wrap">'
        f'<table class="painel-drill-itens">{cabecalho}'
        f'<tbody>{"".join(linhas)}</tbody>'
        "</table>"
        "</div>"
        "</div>"
    )


def _sem_vinculo_html() -> str:
    """Callout exibido quando a transação não tem documento vinculado.

    O botão "ligar manualmente" é placeholder visual -- a persistência
    de vínculos manuais é escopo de sprint futura
    (INFRA-LIGAR-MANUAL). Para evitar quebra de UX, renderizamos apenas
    o callout. O botão real ``st.button`` é instanciado pelo orquestrador.
    """
    return minificar(
        """
        <div class="painel-drill-bloco painel-drill-sem-vinculo">
            <span class="painel-drill-bloco-titulo">DOCUMENTO VINCULADO</span>
            <p class="painel-drill-vazio">
                Sem documento vinculado a esta transação no grafo.
                Quando o matcher (INFRA-LINKING-NFE-TRANSACAO) processar
                NF/cupom equivalente, o vínculo aparece aqui.
            </p>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def renderizar_painel_drill_down(
    transacao: dict[str, Any],
    documento: dict[str, Any] | None = None,
    itens: list[dict[str, Any]] | None = None,
    cruzamentos: list[dict[str, Any]] | None = None,
) -> str:
    """Devolve HTML completo do painel de drill-down (já minificado).

    Função pura. Quando ``documento`` é None, mostra callout de "sem
    vínculo" no lugar do bloco de documento e suprime tabela de itens.
    Quando ``cruzamentos`` é None ou lista vazia, suprime o bloco de
    cruzamentos.
    """
    cabecalho = _header_html(transacao)
    if documento is None:
        bloco_doc = _sem_vinculo_html()
        bloco_itens = ""
    else:
        bloco_doc = _documento_vinculado_html(documento)
        bloco_itens = _itens_html(itens or [])
    bloco_cruzamentos = _cruzamentos_html(cruzamentos or [])

    abertura = minificar(
        '<aside class="painel-drill-down" '
        'role="dialog" aria-label="Drill-down da transação">'
    )
    fechamento = "</aside>"
    return abertura + cabecalho + bloco_doc + bloco_itens + bloco_cruzamentos + fechamento


# ---------------------------------------------------------------------------
# Persistência opcional (revisao_humana.sqlite)
# ---------------------------------------------------------------------------


_SQL_CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS revisao_drill_down (
    transacao_id INTEGER PRIMARY KEY,
    marcado_em TEXT NOT NULL
)
"""


def persistir_revisao(transacao_id: int, db_path: Path) -> bool:
    """Marca a transação como revisada em ``revisao_humana.sqlite``.

    Best-effort: cria a tabela ``revisao_drill_down`` se não existir.
    Quando o arquivo .sqlite NÃO existe, retorna False sem criar
    (graceful degradation -- ADR-10). Quando existe e a inserção é
    bem sucedida, retorna True.

    Idempotente: ``ON CONFLICT(transacao_id) DO UPDATE`` atualiza
    ``marcado_em``.
    """
    if not db_path.exists():
        return False
    from datetime import datetime, timezone

    try:
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(_SQL_CRIAR_TABELA)
            agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.execute(
                "INSERT INTO revisao_drill_down(transacao_id, marcado_em) "
                "VALUES (?, ?) "
                "ON CONFLICT(transacao_id) DO UPDATE SET marcado_em = excluded.marcado_em",
                (int(transacao_id), agora),
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except sqlite3.Error:
        return False


# "Quem entende o item entende o gasto." -- princípio do drill-down
