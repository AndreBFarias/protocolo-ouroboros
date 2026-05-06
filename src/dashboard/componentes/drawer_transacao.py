"""Drawer lateral de inspeção de transação (UX-RD-06).

Painel deslizante 480px à direita exibido quando o usuário "clica" numa
linha da tabela densa do Extrato. Renderiza o JSON completo da transação
com syntax highlight (chaves rosa, strings amarelo, números roxo, bool
laranja, null cinza) e, quando há documento vinculado pelo grafo, mostra
o sha8 e tipo do edge.

Decisão pragmática (Streamlit não tem drawer nativo)
----------------------------------------------------
Streamlit ≥ 1.30 oferece ``st.dialog`` mas é modal centralizado, não
side-drawer. Para preservar a estética do mockup ``02-extrato.html``
(slide-in à direita) optamos por:

1. Emitir o drawer como ``<div class="drawer">`` HTML estático via
   ``st.markdown(..., unsafe_allow_html=True)``.
2. Controlar visibilidade por ``st.session_state["extrato_drawer_idx"]``.
3. Botão "fechar" emite ``st.button`` que faz ``del session_state[...]``
   + ``st.rerun()``.

Trade-off conhecido: o drawer é renderizado dentro do fluxo Streamlit,
não como overlay verdadeiro. Compensamos com ``position: fixed`` na CSS
de ``tema_css.py`` (classe ``.drawer``). Em telas estreitas o drawer
sobrepõe a tabela; em widescreen fica ao lado, espelhando o mockup.

Função pública: ``renderizar_drawer(transacao, doc_vinculado)`` -- pura,  # noqa: accent
não acessa session_state nem chama ``st.button``. O orquestrador (página
extrato) decide quando chamar e como capturar o evento de fechar.
"""

from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd

from src.dashboard.componentes.html_utils import minificar


def _serializar_valor(valor: Any) -> Any:
    """Converte valores não-JSON-nativos (Timestamp, NaN, NaT) em string/None."""
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if pd.isna(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, (int, float, bool, str)):
        return valor
    return str(valor)


def transacao_para_dict(row: pd.Series) -> dict[str, Any]:
    """Converte uma linha do DataFrame extrato num dict serializável.

    Preserva apenas chaves cujo valor é não-nulo. Mantém ordem canônica
    (data, valor, local, categoria, ...) para o drawer ser legível.
    """
    ordem_canonica = [
        "data",
        "valor",
        "local",
        "categoria",
        "classificacao",
        "forma_pagamento",
        "banco_origem",
        "tipo",
        "quem",
        "mes_ref",
        "tag_irpf",
        "obs",
        "identificador",
    ]
    resultado: dict[str, Any] = {}
    for chave in ordem_canonica:
        if chave in row.index:
            valor = _serializar_valor(row.get(chave))
            if valor is not None and valor != "":
                resultado[chave] = valor
    # Acrescenta colunas extras não previstas (a tabela do XLSX pode crescer).
    for chave in row.index:
        if chave in resultado or chave in ordem_canonica:
            continue
        if str(chave).startswith("_"):
            continue  # campos internos (ex: _descricao_original) não vão pro drawer
        valor = _serializar_valor(row.get(chave))
        if valor is not None and valor != "":
            resultado[str(chave)] = valor
    return resultado


def _highlight_json(obj: dict[str, Any]) -> str:
    """Renderiza JSON com syntax highlight via classes ``.syn-*``.

    Tokeniza o JSON formatado num único passo: cada match (string-key,
    string-value, number, bool, null) vira um ``<span class="syn-*">``.
    Single-pass evita o problema de regex aninhado reinterpretando o
    HTML que a passagem anterior injetou.
    """
    import re

    bruto = json.dumps(obj, ensure_ascii=False, indent=2)

    # Escape HTML mínimo. Aplicado APENAS aos pedaços não-token (strings JSON
    # já são double-quoted ASCII na fonte; números/null/bool não têm < > &).
    # Conteúdos sensíveis (valores de string) são escapados dentro do
    # callback após reconhecer o token.
    def _esc(texto: str) -> str:
        return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Padrão único alternando os tipos: chave (lookahead :), string-valor,
    # número, true/false, null.
    padrao = re.compile(
        r'(?P<key>"(?:[^"\\]|\\.)*")\s*:'  # chave + :
        r'|(?P<str>"(?:[^"\\]|\\.)*")'      # string-valor (sem : depois)
        r"|(?P<num>-?\b\d+(?:\.\d+)?\b)"   # número
        r"|(?P<bool>\btrue\b|\bfalse\b)"    # bool
        r"|(?P<null>\bnull\b)"              # null
    )

    saida: list[str] = []
    pos = 0
    for m in padrao.finditer(bruto):
        # Pedaço de pontuação/espaço entre tokens (escape HTML).
        saida.append(_esc(bruto[pos : m.start()]))
        if m.lastgroup == "key":
            saida.append(f'<span class="syn-key">{_esc(m.group("key"))}</span>:')
        elif m.lastgroup == "str":
            saida.append(f'<span class="syn-string">{_esc(m.group("str"))}</span>')
        elif m.lastgroup == "num":
            saida.append(f'<span class="syn-number">{m.group("num")}</span>')
        elif m.lastgroup == "bool":
            saida.append(f'<span class="syn-bool">{m.group("bool")}</span>')
        elif m.lastgroup == "null":
            saida.append('<span class="syn-null">null</span>')
        pos = m.end()
    saida.append(_esc(bruto[pos:]))
    return "".join(saida)


def _doc_vinculado_html(doc: dict[str, Any] | None) -> str:
    """Bloco "Documento vinculado" no rodapé do drawer-body."""
    if not doc:
        return minificar(
            """
            <div class="drawer-doc-vazio">
                <span class="drawer-doc-rotulo">DOCUMENTO VINCULADO</span>
                <p class="drawer-doc-msg">Sem documento vinculado no grafo.</p>
            </div>
            """
        )

    sha8 = str(doc.get("sha8") or doc.get("sha256", "")[:8] or "-")
    tipo_edge = str(doc.get("tipo_edge_semantico") or doc.get("tipo_edge") or "-")
    nome = str(doc.get("nome") or doc.get("path") or "-")

    return minificar(
        f"""
        <div class="drawer-doc">
            <span class="drawer-doc-rotulo">DOCUMENTO VINCULADO</span>
            <div class="drawer-doc-linha">
                <span class="drawer-doc-chave">sha8</span>
                <code class="drawer-doc-valor syn-number">{sha8}</code>
            </div>
            <div class="drawer-doc-linha">
                <span class="drawer-doc-chave">tipo_edge</span>
                <code class="drawer-doc-valor syn-string">{tipo_edge}</code>
            </div>
            <div class="drawer-doc-linha">
                <span class="drawer-doc-chave">nome</span>
                <code class="drawer-doc-valor syn-string">{nome}</code>
            </div>
        </div>
        """
    )


def renderizar_drawer(
    transacao: dict[str, Any],
    doc_vinculado: dict[str, Any] | None = None,
) -> str:
    """Devolve o HTML completo do drawer (já minificado).

    Função pura: não escreve em ``st.session_state`` nem chama ``st.button``.
    O orquestrador injeta com ``st.markdown(..., unsafe_allow_html=True)``.
    """
    json_html = _highlight_json(transacao)
    doc_html = _doc_vinculado_html(doc_vinculado)

    # ``<pre>`` preserva quebras do JSON; ``json_html`` é HTML interno
    # com spans, então NÃO deve ser minificado novamente (perderia as
    # quebras entre linhas do JSON formatado).
    cabecalho_minificado = minificar(
        """
        <div class="drawer-overlay-stub"></div>
        <aside class="drawer" role="dialog" aria-label="Detalhes da transação">
            <div class="drawer-head">
                <span class="drawer-titulo">DETALHES · TRANSAÇÃO</span>
                <span class="drawer-hint">Esc fecha</span>
            </div>
            <div class="drawer-body">
        """
    )
    rodape_minificado = minificar(
        """
            </div>
        </aside>
        """
    )

    # Atenção: NÃO usar ``<pre><code>`` aqui. O Streamlit detecta esse padrão
    # como "code block" e re-empacota como ``stCode``, transformando spans
    # internos em ``[object Object]``. Usamos ``<div>`` com
    # ``white-space: pre`` no CSS (.drawer-json) para preservar quebras de
    # linha sem disparar o caminho do code-block do parser.
    bloco_pre = (
        '<div class="drawer-json">'
        + json_html
        + "</div>"
    )

    return cabecalho_minificado + bloco_pre + doc_html + rodape_minificado


# "O detalhe é o que separa o profissional do amador." -- Charles Eames
