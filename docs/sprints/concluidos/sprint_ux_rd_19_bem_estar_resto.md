---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-19
  title: "Bem-estar resto: Rotina + Recap + Memórias + Medidas + Ciclo + Cruzamentos + Privacidade + Editor TOML"
  prioridade: P1
  estimativa: 4h
  onda: 6
  origem: "mockups 20-rotina.html + 21-recap.html + 23-memorias.html + 24-medidas.html + 25-ciclo.html + 26-cruzamentos.html + 27-privacidade.html + 28-rotina-toml.html"
  depende_de: [UX-RD-16, UX-RD-17, UX-RD-18]
  touches:
    - path: src/dashboard/paginas/be_rotina.py
      reason: "NOVO -- visualização rotina diária baseada em rotina.toml"
    - path: src/dashboard/paginas/be_recap.py
      reason: "NOVO -- recap 7d/30d/90d (toggle) com agregados + insights"
    - path: src/dashboard/paginas/be_memorias.py
      reason: "NOVO -- 3 sub-abas: Treinos (heatmap 91d) + Fotos (galeria) + Marcos (lista)"
    - path: src/dashboard/paginas/be_medidas.py
      reason: "NOVO -- comparativo (peso/cintura/etc) + slider de fotos comparativas frente/lado/costas"
    - path: src/dashboard/paginas/be_ciclo.py
      reason: "NOVO -- calendário menstrual com fases (toggle visibilidade em settings)"
    - path: src/dashboard/paginas/be_cruzamentos.py
      reason: "NOVO -- correlações entre humor × eventos × medidas (read-only, dados de cache)"
    - path: src/dashboard/paginas/be_privacidade.py
      reason: "NOVO -- toggles A↔B: o que pessoa_a vê de pessoa_b e vice-versa (config local)"
    - path: src/dashboard/paginas/be_editor_toml.py
      reason: "NOVO -- textarea com rotina.toml + lint (tomllib) + save em ~/.ouroboros/rotina.toml"
    - path: tests/test_be_resto.py
      reason: "NOVO -- 16 testes: 8 páginas renderizam, recap toggles 7/30/90, ciclo respeita toggle, editor TOML valida sintaxe"
  forbidden:
    - "Quebrar parsers UX-RD-16"
    - "Editor TOML grava em path sem confirmar diretório existir"
  hipotese:
    - "rotina.toml ainda não existe; sprint cria template inicial em ~/.ouroboros/rotina.toml.example. Editor TOML cria se ausente."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_be_resto.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "8 páginas Bem-estar (Rotina, Recap, Memórias, Medidas, Ciclo, Cruzamentos, Privacidade, Editor TOML) renderizam em ?cluster=Bem-estar"
    - "Rotina lê de rotina.toml; se ausente, mostra template + 'Criar rotina'"
    - "Recap: toggle 7d/30d/90d altera agregados (humor médio, eventos, treinos)"
    - "Memórias: 3 sub-abas com heatmap 91d treinos + galeria fotos + lista marcos"
    - "Medidas: comparativo última vs primeira + slider fotos"
    - "Ciclo: respeita toggle on/off (privacidade)"
    - "Cruzamentos: pelo menos 3 correlações visíveis"
    - "Privacidade: 6 toggles (visibilidade pessoa_a↔pessoa_b por schema)"
    - "Editor TOML: textarea + botão 'Validar' (tomllib parse) + 'Salvar' grava em ~/.ouroboros/rotina.toml"
    - "TOML inválido: aviso vermelho com linha do erro"
    - "pytest baseline mantida + 16 testes novos"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # ?cluster=Bem-estar -- 12 abas visíveis (sub-abas)
    # Visitar cada uma das 8 telas restantes
    # Editor TOML: digitar inválido -> erro; salvar -> ~/.ouroboros/rotina.toml gravado
    cat ~/.ouroboros/rotina.toml
    # screenshots agregados em UX-RD-19_*.png
```

---

# Sprint UX-RD-19 — Bem-estar resto consolidado

**Status:** BACKLOG

Sprint final do redesign. Consolida 8 telas em 1 sprint pesada — cada uma é
predominantemente leitura do cache + render.

**Validação visual do dono:** abrir cada uma das 8 abas, conferir vs mockup
correspondente. Última checagem: `./run.sh --dashboard` e fazer um tour
completo de todos 8 clusters + 28 telas para confirmar coerência total.

**Sprint final** = momento de fechar o `REDESIGN_INDEX.md` com todas marcadas
concluída e mover specs para `concluidos/`.

---

*"O fim de um trabalho é o começo de outro." — adaptado de Leonardo da Vinci*
