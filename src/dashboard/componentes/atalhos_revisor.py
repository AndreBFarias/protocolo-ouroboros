"""Atalhos de teclado restritos à página Revisor — Sprint UX-RD-10.

Espelha o contrato dos mockups ``09-revisor.html`` (atalhos j/k/a/r) num
listener Python+Streamlit injetado via ``st.components.v1.html(..., height=0)``.

Atalhos suportados (somente quando ``?cluster=Documentos&tab=Revisor``):

  * ``j``  -> próximo card (scrolla para próxima divergência)
  * ``k``  -> card anterior (scrolla para divergência prévia)
  * ``a``  -> aprova o card focado (clica botão ``data-revisor-aprovar``)
  * ``r``  -> rejeita o card focado (clica botão ``data-revisor-rejeitar``)

Princípios:
  * O JS sai mudo se a query string atual não for o Revisor (evita poluir
    Hoje/Análise/IRPF com tecla ``a`` que ali não tem semântica).
  * Guard contra ``input``/``textarea``/``select``/``[contenteditable]``
    para não atrapalhar digitação em filtros/observações.
  * ``Esc`` é roteado para o atalho global da Sprint UX-RD-03 (que fecha
    modais); aqui não tratamos para não duplicar listeners.
  * Idempotência: registra ``window.parent.__ouroborosRevisorAtalhosInstalados``
    para impedir múltiplos listeners empilhados em re-runs do Streamlit.

Segurança XSS: sem interpolação de input do usuário em runtime. Os seletores
``[data-revisor-card]``, ``[data-revisor-aprovar]``, ``[data-revisor-rejeitar]``
são literais hardcoded e correspondem a atributos emitidos pelo
``revisor.py`` no markup do card.
"""

from __future__ import annotations


def gerar_html_atalhos_revisor() -> str:
    """Devolve HTML+JS pronto para ``st.components.v1.html(html, height=0)``.

    O bloco contém um único listener ``keydown`` que:

    1. Verifica se a URL atual é a página Revisor (``cluster=Documentos`` e
       ``tab=Revisor``); se não for, retorna sem registrar nada.
    2. Mantém um índice ``__ouroborosRevisorIndex`` de qual card está focado.
       ``j`` incrementa, ``k`` decrementa (clamp em [0, n-1]).
    3. ``a`` / ``r`` clicam o botão correspondente do card focado.
    4. Scroll suave para o card focado quando navegação ocorre.
    """
    return """
<script>
(function() {
  var docTopo = (window.parent && window.parent.document)
    ? window.parent.document
    : document;
  var winTopo = window.parent || window;

  // Idempotência: só instala uma vez por sessão de browser.
  if (winTopo.__ouroborosRevisorAtalhosInstalados) {
    return;
  }
  winTopo.__ouroborosRevisorAtalhosInstalados = true;

  function paginaERevisor() {
    try {
      var qs = winTopo.location.search || '';
      // Aceita "Revisor" (com R maiúsculo, como no deep-link UX-RD-03).
      // O cluster pode vir codificado (Documentos com "ó" mascarado, ou
      // simplesmente "Documentos"). Comparamos por substring.
      return qs.indexOf('cluster=Documentos') !== -1
          && qs.indexOf('tab=Revisor') !== -1;
    } catch (e) {
      return false;
    }
  }

  function cards() {
    return docTopo.querySelectorAll('[data-revisor-card]');
  }

  function focarCard(idx) {
    var todos = cards();
    if (!todos.length) { return; }
    if (idx < 0) { idx = 0; }
    if (idx >= todos.length) { idx = todos.length - 1; }
    winTopo.__ouroborosRevisorIndex = idx;
    var alvo = todos[idx];
    if (alvo && alvo.scrollIntoView) {
      alvo.scrollIntoView({behavior: 'smooth', block: 'center'});
    }
    todos.forEach(function(c, i) {
      if (i === idx) {
        c.setAttribute('data-revisor-foco', '1');
      } else {
        c.removeAttribute('data-revisor-foco');
      }
    });
  }

  function clicarAcao(prefixoTexto) {
    var idx = winTopo.__ouroborosRevisorIndex || 0;
    var todos = cards();
    if (!todos.length || idx >= todos.length) { return; }
    var card = todos[idx];
    // Streamlit renderiza st.button como <button>. Procuramos pelo prefixo do
    // texto exibido (\"Aprovar (a)\" / \"Rejeitar (r)\") dentro do card focado.
    var botoes = card.querySelectorAll('button');
    for (var i = 0; i < botoes.length; i++) {
      var txt = (botoes[i].innerText || botoes[i].textContent || '').trim();
      if (txt.indexOf(prefixoTexto) === 0) {
        botoes[i].click();
        return;
      }
    }
  }

  docTopo.addEventListener('keydown', function(e) {
    if (!paginaERevisor()) { return; }
    var alvo = e.target;
    if (alvo && alvo.matches
        && alvo.matches('input, textarea, select, [contenteditable="true"]')) {
      return;
    }
    if (e.key === 'j' || e.key === 'J') {
      e.preventDefault();
      var atualJ = winTopo.__ouroborosRevisorIndex;
      if (atualJ === undefined || atualJ === null) { atualJ = -1; }
      focarCard(atualJ + 1);
      return;
    }
    if (e.key === 'k' || e.key === 'K') {
      e.preventDefault();
      var atualK = winTopo.__ouroborosRevisorIndex;
      if (atualK === undefined || atualK === null) { atualK = 1; }
      focarCard(atualK - 1);
      return;
    }
    if (e.key === 'a' || e.key === 'A') {
      e.preventDefault();
      clicarAcao('Aprovar');
      return;
    }
    if (e.key === 'r' || e.key === 'R') {
      e.preventDefault();
      clicarAcao('Rejeitar');
      return;
    }
  });
})();
</script>
"""


# "Quem domina o teclado domina o ritmo da revisão." -- princípio do ergonômico
