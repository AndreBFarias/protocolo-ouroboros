## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-18
  title: "Diário emocional + Eventos: lista cronológica trigger/vitória + timeline"
  prioridade: P1
  estimativa: 4h
  onda: 6
  origem: "mockups 19-diario-emocional.html + 22-eventos.html"
  depende_de: [UX-RD-16]
  touches:
    - path: src/dashboard/paginas/be_diario.py
      reason: "NOVO -- lista cronológica de diários com border-left (red=trigger, green=vitória), chips emoção, slider intensidade, filtro trigger/vitória/período"
    - path: src/dashboard/paginas/be_eventos.py
      reason: "NOVO -- timeline cronológica de eventos com mapa de bairros (lista bairros + count) + thumbs de fotos, filtro positivo/negativo"
    - path: src/mobile_cache/escrever_diario.py
      reason: "NOVO -- writer ao vault para inbox/mente/diario/<YYYY-MM-DD>/<slug>.md"
    - path: src/mobile_cache/escrever_evento.py
      reason: "NOVO -- writer ao vault para eventos/<YYYY-MM-DD>/<slug>.md"
    - path: tests/test_be_diario_eventos.py
      reason: "NOVO -- 10 testes: filtros funcionam, border-left correta, intensidade slider 1-5, escrever_diario gera .md válido, timeline ordenação desc"
  forbidden:
    - "Quebrar parsers UX-RD-16 (read-only)"
    - "Hardcodar bairros -- agregar de eventos.json cache"
  hipotese:
    - "Schema diário tem modo 'trigger' ou 'vitoria' no frontmatter. Schema evento tem 'positivo' ou 'negativo' + 'bairro'. Confirmar via fixture."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_be_diario_eventos.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "?cluster=Bem-estar&tab=Diário+emocional -- lista de cards com border-left red/green"
    - "Cada card: data + modo (trigger/vitória) + chips emoção + slider intensidade visual + frase + 'com quem'"
    - "Filtros: modo (radio), período (selectbox), pessoa"
    - "?cluster=Bem-estar&tab=Eventos -- timeline cronológica desc"
    - "Cards evento: data + modo (positivo/negativo) + lugar+bairro + slider 1-5 + thumbs fotos"
    - "Lateral Eventos: lista de bairros com count (top 10)"
    - "Botões 'Registrar diário' e 'Registrar evento' abrem form modal -> grava no vault"
    - "Vault inexistente: graceful"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # ?cluster=Bem-estar&tab=Diário+emocional -- lista visível
    # ?cluster=Bem-estar&tab=Eventos -- timeline visível
    # screenshots vs 19 e 22
```

---

# Sprint UX-RD-18 — Diário emocional + Eventos

**Status:** BACKLOG

Telas com **escrita ao vault** — confirmar com mobile que arquivos
sincronizam corretamente.

---

*"O que se nomeia, se atravessa." — princípio terapêutico*
