## 0. SPEC (machine-readable)

```yaml
sprint:
  id: DEBT-UX-RD-06.A
  title: "Refatorar extrato.py (1069L) extraindo estilos locais e helpers HTML para arquivos dedicados"
  prioridade: P2
  estimativa: 1h
  origem: "achado colateral 2026-05-04 em UX-RD-06: reescrita 1:1 do mockup levou extrato.py de 473L para 1069L, ultrapassando limite 800L do CLAUDE.md §convenções"
  touches:
    - src/dashboard/paginas/extrato.py (extrair seções; manter como orquestrador puro ~400L)
    - src/dashboard/paginas/_extrato_estilos.py (NOVO -- ~250L de estilos locais CSS)
    - src/dashboard/componentes/extrato_visual.py (NOVO -- helpers HTML _saldo_topo_html, _tabela_densa_html, _breakdown_lateral_html)
    - tests/test_extrato_redesign.py (atualizar imports se referência interna for tocada)
  forbidden:
    - "Mudar comportamento (visual ou funcional) -- só refactor"
    - "Tocar drawer_transacao.py ou html_utils.py"
    - "Tocar tema_css.py ou tokens"
  hipotese:
    - "extrato.py atual tem 4 blocos isoláveis: estilos locais (top do arquivo, ~250L), saldo_topo (~80L), tabela_densa (~250L), breakdown_lateral (~80L). Confirmar via grep dos cabeçalhos de função antes de codar."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_extrato_redesign.py -v"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "extrato.py ≤ 800L (limite CLAUDE.md respeitado)"
    - "_extrato_estilos.py exporta uma função pública estilos_locais_html() retornando string"
    - "extrato_visual.py exporta saldo_topo_html, tabela_densa_html, breakdown_lateral_html (signature compatível com chamadas atuais)"
    - "Comportamento visual idêntico (screenshot pós-refactor casa pixel-a-pixel com docs/auditorias/redesign/UX-RD-06.png)"
    - "pytest baseline mantida (≥2265)"
    - "make smoke 10/10"
  proof_of_work_esperado: |
    # AC: limites
    wc -l src/dashboard/paginas/extrato.py
    # esperado <= 800

    wc -l src/dashboard/paginas/_extrato_estilos.py src/dashboard/componentes/extrato_visual.py
    # esperado: ~250 e ~400 respectivamente

    # AC: equivalência visual
    setsid -f .venv/bin/streamlit run src/dashboard/app.py --server.port 8521 --server.headless true > /tmp/strm.log 2>&1 < /dev/null
    sleep 8
    # screenshot via playwright local + sha256 comparado com UX-RD-06.png
```

---

# Sprint DEBT-UX-RD-06.A — Refatorar extrato.py

**Status:** BACKLOG (P2, anti-débito)

Achado colateral formalizado em 2026-05-04 durante UX-RD-06. A reescrita
1:1 do mockup `02-extrato.html` levou `extrato.py` de 473L para 1069L,
ultrapassando o limite de 800L declarado em `CLAUDE.md §convenções`.

**Decisão do supervisor:** aceitar a violação temporariamente para entregar
UX-RD-06 visualmente completa, e formalizar esta sub-sprint imediatamente
(zero follow-up). A refatoração é puramente estética/manutenção — sem
mudança visual ou funcional. Não bloqueia próximas sprints UX-RD-XX.

**Pode rodar em qualquer momento entre UX-RD-06 e UX-RD-19.**

---

*"Código que cresceu além do limite é resposta certa pra pergunta errada." — princípio do refactor lúcido*
