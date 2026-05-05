"""Atalhos globais de teclado para o dashboard — Sprint UX-RD-03.

Espelha o contrato de ``novo-mockup/_shared/shell.js`` (função
``_instalarAtalhos``) em Python+Streamlit. O JS é injetado uma única vez
por sessão via ``st.components.v1.html(..., height=0)``.

Atalhos suportados:

  * ``g h``  -> Home (Visão Geral)
  * ``g i``  -> Inbox
  * ``g v``  -> Documentos / Validação por Arquivo (legado UX-114; UX-RD-11
    troca para Extração + Tripla quando Validação por Arquivo for absorvida)
  * ``g r``  -> Documentos / Revisor
  * ``g f``  -> Análise / IRPF
  * ``g c``  -> Documentos / Catalogação
  * ``/``    -> foca o primeiro ``<input>`` da sidebar
  * ``?``    -> toggle do modal ``#ouroboros-ajuda-overlay`` com tabela dos atalhos
  * ``Esc``  -> fecha o modal de ajuda quando aberto

O buffer ``g`` + segunda letra usa timeout 800ms (mesmo do mockup). O
listener instala um guard ``if (e.target.matches('input, textarea')) return;``
para não atrapalhar digitação. Navegação entre clusters/abas usa o
deep-link da Sprint 100 (``?cluster=X&tab=Y`` via
``window.location.search``).

Segurança XSS: o HTML embutido no script vem exclusivamente de constantes
literais hardcoded neste módulo (descrições e combinações de teclas). Não
há interpolação de input do usuário em runtime. As linhas da tabela de
ajuda são montadas via DOM API (``createElement`` / ``textContent``) -- sem
``innerHTML`` para conteúdo dinâmico.
"""

from __future__ import annotations

# Map de atalhos -> URL relativa (apenas query string). O JS prefixa com
# ``window.location.pathname`` para preservar o host:porta atual.
_ATALHOS: tuple[tuple[str, str, str], ...] = (
    ("gh", "?cluster=Home", "Home (Visão Geral)"),
    ("gi", "?cluster=Inbox", "Inbox"),
    (
        "gv",
        "?cluster=Documentos&tab=Validação+por+Arquivo",
        "Documentos / Validação por Arquivo",
    ),
    ("gr", "?cluster=Documentos&tab=Revisor", "Documentos / Revisor"),
    ("gf", "?cluster=Análise&tab=IRPF", "Análise / IRPF"),
    ("gc", "?cluster=Documentos&tab=Catalogação", "Documentos / Catalogação"),
)

# Linhas extras (atalhos não-letra) com nomes amigáveis. Mantidas separadas
# de ``_ATALHOS`` porque não geram navegação -- só aparecem na tabela do
# modal de ajuda.
_ATALHOS_EXTRA: tuple[tuple[str, str], ...] = (
    ("/", "Focar busca"),
    ("?", "Esta ajuda"),
    ("Esc", "Fechar overlay"),
)


def _mapa_js() -> str:
    """Serializa ``_ATALHOS`` num literal JS ``{combo: url}``.

    Apenas combinações letra+letra entram no mapa (as três entradas de
    ``_ATALHOS_EXTRA`` são tratadas inline pelo listener).
    """
    pares: list[str] = []
    for combo, alvo, _descricao in _ATALHOS:
        # combo e alvo são literais hardcoded -- sem input do usuário,
        # sem aspas internas (assert defensivo abaixo).
        assert '"' not in combo and '"' not in alvo, "combo/alvo com aspas"
        pares.append(f'"{combo}": "{alvo}"')
    return "{" + ", ".join(pares) + "}"


def _linhas_modal_js() -> str:
    """Devolve um literal JS com array ``[[tecla, descrição], ...]``.

    O JS popula a tabela do modal via ``createElement`` + ``textContent``,
    o que evita injeção XSS mesmo se uma constante futura introduzir
    caracteres especiais.
    """
    pares: list[str] = []
    for combo, _alvo, descricao in _ATALHOS:
        legenda = " ".join(combo)
        pares.append(_par_js(legenda, descricao))
    for tecla, descricao in _ATALHOS_EXTRA:
        pares.append(_par_js(tecla, descricao))
    return "[" + ", ".join(pares) + "]"


def _par_js(tecla: str, descricao: str) -> str:
    """Formata um par ``["tecla", "descricao"]`` escapando aspas."""
    tecla_esc = tecla.replace("\\", "\\\\").replace('"', '\\"')
    descricao_esc = descricao.replace("\\", "\\\\").replace('"', '\\"')
    return f'["{tecla_esc}", "{descricao_esc}"]'


def gerar_html_atalhos() -> str:
    """Devolve HTML+JS pronto para ``st.components.v1.html(html, height=0)``.

    O bloco contém:

    1. Listener ``keydown`` no ``window.parent.document`` que captura buffer
       ``g`` + segunda letra (timeout 800ms), redireciona via
       ``window.parent.location`` para o deep-link mapeado.
    2. Hotkeys diretas: ``/`` foca ``input`` da sidebar (Streamlit cria o
       campo de busca como ``<input>`` dentro de
       ``[data-testid="stSidebar"]``); ``?`` abre/fecha modal de ajuda;
       ``Esc`` fecha modal.
    3. Modal ``#ouroboros-ajuda-overlay`` injetado on-demand via DOM API
       (sem ``innerHTML`` com dados dinâmicos).

    Idempotência: o script registra ``window.parent.__ouroborosAtalhosInstalados``
    para impedir múltiplos listeners empilhados quando o Streamlit
    re-executa o ``components.html`` em re-runs.
    """
    mapa_js = _mapa_js()
    linhas_modal_js = _linhas_modal_js()
    return f"""
<script>
(function() {{
  var docTopo = (window.parent && window.parent.document)
    ? window.parent.document
    : document;
  var winTopo = window.parent || window;
  if (winTopo.__ouroborosAtalhosInstalados) {{
    return;
  }}
  winTopo.__ouroborosAtalhosInstalados = true;

  var mapa = {mapa_js};
  var linhasModal = {linhas_modal_js};
  var buffer = '';
  var timer = null;

  function navegarPara(query) {{
    try {{
      var loc = winTopo.location;
      var origem = loc.origin + loc.pathname;
      winTopo.location.href = origem + query;
    }} catch (e) {{
      /* graceful: cross-origin pode bloquear */
    }}
  }}

  function focarBusca() {{
    var input = docTopo.querySelector(
      '[data-testid="stSidebar"] input, .sidebar-search input'
    );
    if (input) {{
      input.focus();
    }}
  }}

  function montarModal() {{
    var overlay = docTopo.createElement('div');
    overlay.id = 'ouroboros-ajuda-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);'
      + 'z-index:9999;display:grid;place-items:center;';

    var card = docTopo.createElement('div');
    card.className = 'card';
    card.style.cssText = 'min-width:480px;max-width:560px;'
      + 'background:var(--bg-elevated,#1e1e2e);'
      + 'border:1px solid var(--border-subtle,#313244);'
      + 'border-radius:8px;padding:16px;color:inherit;';

    var head = docTopo.createElement('div');
    head.className = 'card-head';
    head.style.cssText = 'display:flex;align-items:center;'
      + 'justify-content:space-between;margin-bottom:12px;';
    var titulo = docTopo.createElement('h3');
    titulo.className = 'card-title';
    titulo.style.cssText = 'margin:0;font-family:var(--ff-mono,monospace);'
      + 'font-size:14px;';
    titulo.textContent = 'Atalhos de teclado';
    var btnFechar = docTopo.createElement('button');
    btnFechar.className = 'btn btn-icon btn-ghost';
    btnFechar.style.cssText = 'background:transparent;border:0;color:inherit;'
      + 'cursor:pointer;font-size:18px;';
    btnFechar.textContent = 'x';
    btnFechar.addEventListener('click', fecharAjuda);
    head.appendChild(titulo);
    head.appendChild(btnFechar);

    var tabela = docTopo.createElement('table');
    tabela.style.cssText = 'width:100%;font-size:13px;';
    linhasModal.forEach(function(linha) {{
      var tr = docTopo.createElement('tr');
      var tdTecla = docTopo.createElement('td');
      tdTecla.style.cssText = 'padding:6px 0;';
      var kbd = docTopo.createElement('kbd');
      kbd.className = 'kbd';
      kbd.textContent = linha[0];
      tdTecla.appendChild(kbd);
      var tdDesc = docTopo.createElement('td');
      tdDesc.textContent = linha[1];
      tr.appendChild(tdTecla);
      tr.appendChild(tdDesc);
      tabela.appendChild(tr);
    }});

    card.appendChild(head);
    card.appendChild(tabela);
    overlay.appendChild(card);
    overlay.addEventListener('click', function(ev) {{
      if (ev.target === overlay) {{ fecharAjuda(); }}
    }});
    return overlay;
  }}

  function abrirAjuda() {{
    var existente = docTopo.getElementById('ouroboros-ajuda-overlay');
    if (existente) {{
      existente.remove();
      return;
    }}
    docTopo.body.appendChild(montarModal());
  }}

  function fecharAjuda() {{
    var existente = docTopo.getElementById('ouroboros-ajuda-overlay');
    if (existente) {{
      existente.remove();
    }}
  }}

  docTopo.addEventListener('keydown', function(e) {{
    var alvo = e.target;
    if (alvo && alvo.matches
        && alvo.matches('input, textarea, select, [contenteditable="true"]')) {{
      return;
    }}
    if (e.key === '/') {{
      e.preventDefault();
      focarBusca();
      return;
    }}
    if (e.key === '?') {{
      e.preventDefault();
      abrirAjuda();
      return;
    }}
    if (e.key === 'Escape') {{
      fecharAjuda();
      return;
    }}
    if (!e.key || e.key.length !== 1) {{
      return;
    }}
    buffer += e.key.toLowerCase();
    if (timer) {{ clearTimeout(timer); }}
    timer = setTimeout(function() {{ buffer = ''; }}, 800);
    if (mapa[buffer]) {{
      var alvoQuery = mapa[buffer];
      buffer = '';
      navegarPara(alvoQuery);
    }} else if (buffer.length >= 2) {{
      buffer = e.key.toLowerCase();
    }}
  }});
}})();
</script>
"""


# "A liberdade está nos dedos: que aprendam a falar." -- Heráclito
