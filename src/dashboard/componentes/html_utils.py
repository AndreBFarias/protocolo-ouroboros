"""Utilitários para emissão segura de HTML em ``st.markdown``.

Lição UX-RD-04 canonizada: o parser CommonMark do Streamlit interpreta
qualquer linha com indentação ≥ 4 espaços como bloco ``<pre><code>``. HTML
gerado a partir de strings Python multiline tem essa indentação por padrão
e, quando emitido cru, vaza fragmentos como ``<tr>``, ``<td>`` e ``<span>``
literais na página.

Solução canônica: colapsar todo whitespace consecutivo num único espaço
antes de injetar, deixando o HTML "numa linha só". O parser CommonMark deixa
de enxergar indentação e o navegador ignora os whitespaces colapsados sem
prejuízo visual.

Uso::

    from src.dashboard.componentes.html_utils import minificar

    html = minificar(f'''
        <div class="card">
            <h3>{titulo}</h3>
        </div>
    ''')
    st.markdown(html, unsafe_allow_html=True)

Histórico: ``_minificar`` foi inicialmente duplicado em ``paginas/visao_geral.py``
(UX-RD-04) e ``paginas/styleguide.py`` (UX-RD-05). UX-RD-06 promove o helper
ao módulo ``componentes/html_utils.py`` para reuso em ``extrato.py`` e
``drawer_transacao.py`` sem duplicação adicional.
"""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")


def minificar(html: str) -> str:
    """Colapsa whitespace consecutivo num único espaço e remove pontas.

    Não mexe em conteúdo dentro de ``<pre>``/``<code>`` porque o uso típico
    é HTML estrutural. Para emitir blocos de código preservando quebras,
    use markup direto (sem indentação Python) ou ``st.code``.
    """
    return _WHITESPACE.sub(" ", html).strip()


# "Concisão é a alma do espírito." -- Shakespeare, Hamlet
