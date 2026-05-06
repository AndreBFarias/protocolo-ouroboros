## 0. SPEC (machine-readable)

```yaml
sprint:
  id: LINT-ACC-01
  title: "Limpar 11 violações de acentuação pré-existentes detectadas em make lint"
  prioridade: P2
  estimativa: 30min
  origem: "executor-sprint UX-RD-01 capturou make lint VERMELHO no baseline da Fase ANTES; 11 violações em 4 arquivos fora do escopo da sprint corrente"
  bloqueia: []
  bloqueado_por: []
  touches:
    - path: docs/sprints/concluidos/sprint_garantia_expirando_01_warning_intermediario.md
      reason: "Linha 3 com 'migracao' e duas ocorrências de 'nao' sem acento"
    - path: docs/sprints/backlog/sprint_micro_01a_followup_nfce_reais.md
      reason: "Linha 23 com 'transacao' sem acento"
    - path: novo-mockup/README.md
      reason: "Linhas 34 ('validacao'), 38 ('analise')"
    - path: novo-mockup/docs/MAPA_FEATURES_MOBILE_DESKTOP.md
      reason: "Linhas 79 ('relatorios'), 89 ('Analise'), 103 ('validacao'), 134 ('execucao'), 136 ('validacao')"
  forbidden:
    - "Tocar src/, tests/, .streamlit/ -- escopo é apenas docs e novo-mockup"
    - "Adicionar '# noqa: accent' em arquivos .md (markdown não parseia comentário Python)"
  hipotese:
    - "Todas as 11 violações são corrigíveis com acentuação correta sem alterar semântica do texto. Nenhuma é identificador de código."
  acceptance_criteria:
    - "make lint exit 0"
    - "Nenhum diff em src/ ou tests/"
    - "Conteúdo semântico dos 4 arquivos preservado (apenas acentuação)"
  tests:
    - cmd: "make lint"
  proof_of_work_esperado: |
    # Antes
    make lint 2>&1 | grep "Acentuação:"
    # = "Acentuação: 11 problema(s) encontrado(s)"

    # Depois
    make lint 2>&1 | tail -2
    # = "Acentuação: OK" (ou simplesmente exit 0)
```

---

# Sprint LINT-ACC-01 — Dívida de acentuação pré-existente

**Status:** BACKLOG
**Origem:** capturada pelo executor-sprint UX-RD-01 durante o passo de baseline (Fase ANTES, item 5 do CLAUDE.md). `make lint` estava VERMELHO antes mesmo de tocar código, com 11 violações em 4 arquivos -- todos fora do escopo touches da sprint UX-RD-01. Conforme protocolo anti-débito do executor: achado colateral não vira fix inline silencioso, vira sprint-filha formal.

**Por que P2:** dívida cosmética, não bloqueia runtime nem testes. Mas a constituição técnica trata acentuação PT-BR como regra inviolável (#1), então precisa fechar em breve. 30 minutos de trabalho mecânico.

**Procedimento:** edição manual nas 11 linhas listadas. `make lint` ao final deve fechar exit 0 (com a ressalva de que outras áreas do repo podem ter dívida não detectada -- esta sprint cobre apenas o que aparece no make lint atual).

---

*"Pequenos detalhes não são detalhes, são o design." -- Charles Eames*
