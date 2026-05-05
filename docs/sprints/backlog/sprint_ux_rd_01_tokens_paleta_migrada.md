## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-01
  title: "Migrar paleta + tokens de tema.py para a nova paleta dos mockups, mantendo aliases backward-compat"
  prioridade: P0
  estimativa: 2h
  onda: 0
  origem: "redesign aprovado 2026-05-04 + mockups novo-mockup/_shared/tokens.css"
  bloqueia: [UX-RD-02, UX-RD-03, todas as demais UX-RD-*]
  touches:
    - path: src/dashboard/tema.py
      reason: "CORES novo dict com bg-base #0e0f15, bg-surface #1a1d28, bg-elevated #232735, bg-inset #0a0b10, texto_sec, texto_muted, tokens D7 (graduado/calibracao/regredindo/pendente), humano (aprovado/rejeitado/revisar/pendente)"
    - path: .streamlit/config.toml
      reason: "backgroundColor=#0e0f15, secondaryBackgroundColor=#1a1d28, primaryColor=#bd93f9 (já era), font=sans serif"
    - path: tests/test_tema_tokens_redesign.py
      reason: "NOVO -- 8 testes regressivos: cada token novo existe em CORES, aliases legacy ('fundo','card_fundo','texto') resolvem para cores novas, MAPA_CLASSIFICACAO continua válido, dict não tem hex duplicados"
  forbidden:
    - "Apagar aliases 'fundo', 'card_fundo', 'texto', 'texto_sec', 'positivo', 'negativo' etc -- páginas legacy ainda usam"
    - "Tocar tema_css.py (UX-RD-02) ou app.py (UX-RD-03)"
    - "Hardcodar hex em qualquer lugar fora de tema.py + .streamlit/config.toml"
  hipotese:
    - "src/dashboard/tema.py linhas 19-49 é o único lugar onde DRACULA + CORES estão definidos. Validar com grep antes de codar."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_tema_tokens_redesign.py -v"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "CORES['fundo'] == '#0e0f15' (era #282A36)"
    - "CORES['card_fundo'] == '#1a1d28' (era #44475A)"
    - "CORES['card_elevado'] == '#232735' (NOVO)"
    - "CORES['fundo_inset'] == '#0a0b10' (NOVO)"
    - "CORES['texto_sec'] == '#a8a9b8' (NOVO -- antes era #c9c9cc legacy)"
    - "CORES['texto_muted'] == '#6c6f7d' (NOVO)"
    - "Tokens D7 presentes: d7_graduado=#6b8e7f, d7_calibracao=#f1fa8c, d7_regredindo=#ffb86c, d7_pendente=#6c6f7d"
    - "Tokens validação humana presentes: humano_aprovado, humano_rejeitado, humano_revisar, humano_pendente"
    - ".streamlit/config.toml com backgroundColor=#0e0f15 e secondaryBackgroundColor=#1a1d28"
    - "Aliases legacy ('fundo','card_fundo','texto','positivo','negativo','destaque','superfluo','obrigatorio','questionavel','na','neutro','alerta','info') TODOS resolvem para hex válido"
    - "pytest tests/ -q baseline ≥2.018 mantida"
    - "make smoke 10/10"
  proof_of_work_esperado: |
    # Hipótese validada com grep
    grep -n "DRACULA\|CORES = " src/dashboard/tema.py
    # = 19,34 (esperado)

    # AC tokens novos
    .venv/bin/python -c "from src.dashboard.tema import CORES; assert CORES['fundo']=='#0e0f15'; assert CORES['card_elevado']=='#232735'; assert CORES['d7_graduado']=='#6b8e7f'; print('OK')"
    # = OK

    # AC config.toml
    grep "backgroundColor\|secondaryBackgroundColor" .streamlit/config.toml
    # = backgroundColor = "#0e0f15"
    # = secondaryBackgroundColor = "#1a1d28"

    # Probe runtime: dashboard renderiza sem crash
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/ -- background visivelmente mais escuro
    # screenshot salvo em docs/auditorias/redesign/UX-RD-01.png
```

---

# Sprint UX-RD-01 — Tokens novos + paleta migrada

**Status:** BACKLOG

Primeira sprint da reforma. Migra apenas os valores hex em `tema.py` e
`.streamlit/config.toml`. Nada de CSS, nada de páginas. Por design.

**Por quê isolada:** se as 14 páginas existentes quebrarem com a paleta nova,
descobrimos imediatamente, antes de a reforma de CSS amplificar o problema.
Aliases backward-compat preservam todos os nomes legados — `fundo`,
`card_fundo`, `texto` continuam resolvendo, só o hex muda.

**Validação visual do dono:** abrir dashboard antes e depois. Comparar lado-a-lado.
Esperado: tudo muito mais escuro, mas funcional.

**Specs absorvidas:** nenhuma (é gate inicial).

---

*"Sem fundamento sólido, o resto desaba." — Sêneca*
