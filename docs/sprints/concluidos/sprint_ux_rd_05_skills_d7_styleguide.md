---
concluida_em: 2026-05-04
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-05
  title: "Cluster Sistema: Skills D7 dashboard + Styleguide vivo"
  prioridade: P1
  estimativa: 2h
  onda: 1
  origem: "mockups 14-skills-d7.html + styleguide.html"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/skills_d7.py
      reason: "NOVO -- dashboard analítico de skills D7: contagens por estado (graduado/calibrando/regredindo/pendente), gráfico evolução, lista clicável drill-down"
    - path: src/dashboard/paginas/styleguide.py
      reason: "NOVO -- renderiza tokens reais de tema.py + tema_css.py: paleta, tipografia, KPI demo, pills D7 demo, drawer demo. QA visual."
    - path: src/dashboard/app.py
      reason: "Cluster Sistema dispatch: ['Skills D7', 'Styleguide']"
    - path: tests/test_sistema_redesign.py
      reason: "NOVO -- 4 testes: skills_d7 renderiza, styleguide renderiza, cluster Sistema acessível via ?cluster=Sistema"
  forbidden:
    - "Inventar dados de skills -- ler de fonte real (skill_d7_log.json ou similar; se ausente, fallback para snapshot vazio com aviso 'D7 ainda não inicializado')"
  hipotese:
    - "Não há fonte D7 estruturada hoje (só skill /auditar-cobertura-total que é manual). Sprint cria reader leve com fallback graceful."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_sistema_redesign.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "?cluster=Sistema mostra 2 abas: Skills D7 e Styleguide"
    - "Skills D7: 4 KPIs (graduado/calibrando/regredindo/pendente) + lista skills com pill D7 + last_run timestamp"
    - "Styleguide: tabela paleta (todos os tokens com swatch + hex + var-name) + tipografia demo (todos --fs-*) + KPI demo + pills D7 + drawer mock + table densa demo"
    - "Sem dados D7 reais: aviso 'Cobertura D7 ainda não inicializada -- rode /auditar-cobertura-total'"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # 1. http://localhost:8520/?cluster=Sistema -- 2 abas
    # 2. Aba Skills D7 -- KPIs visíveis (mesmo zerados)
    # 3. Aba Styleguide -- swatches da paleta, todos tokens visíveis
    # screenshot UX-RD-05_skills.png + UX-RD-05_styleguide.png
```

---

# Sprint UX-RD-05 — Skills D7 + Styleguide

**Status:** BACKLOG

Cluster Sistema serve dois propósitos:
1. **Skills D7** — observabilidade do estado de aprendizado das skills.
2. **Styleguide vivo** — QA visual obrigatório das próximas sprints. Cada
   spec UX-RD-XX da Onda 2-6 deve casar com elementos do styleguide.

Validação visual do dono: comparar Styleguide com `novo-mockup/styleguide.html`
lado-a-lado. Se algo no Styleguide não casa, é bug do tema_css.py
(volta para UX-RD-02).

---

*"O que se mede, se gerencia." — Peter Drucker*
