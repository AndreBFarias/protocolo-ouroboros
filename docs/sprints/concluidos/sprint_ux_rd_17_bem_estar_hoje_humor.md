---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-17
  title: "Bem-estar Hoje + Humor heatmap (overlay pessoa_a/pessoa_b)"
  prioridade: P1
  estimativa: 4h
  onda: 6
  origem: "mockups 17-bem-estar-hoje.html + 18-humor-heatmap.html"
  depende_de: [UX-RD-16]
  touches:
    - path: src/dashboard/paginas/be_hoje.py
      reason: "NOVO -- agregador do dia: hero esquerda (humor + sliders) + coluna direita (diários do dia + eventos do dia + medidas do dia)"
    - path: src/dashboard/paginas/be_humor.py
      reason: "NOVO -- heatmap 13×7 (91 dias) com overlay pessoa_a/pessoa_b 50% opacity + form de registro rápido (4 sliders + medicação + sono + chips + textarea)"
    - path: src/dashboard/componentes/heatmap_humor.py
      reason: "NOVO -- gerador HTML grid 13×7 com cores por intensidade humor (1-5) + overlay; reutilizado por be_hoje.py e be_humor.py"
    - path: src/mobile_cache/escrever_humor.py
      reason: "NOVO -- writer ao vault: salva daily/<YYYY-MM-DD>.md com frontmatter; idempotente (overwrite mesmo dia)"
    - path: tests/test_be_hoje_humor.py
      reason: "NOVO -- 8 testes: hero renderiza, heatmap 91 cells, overlay 50% opacity, registrar humor grava .md no vault, próxima leitura mostra novo dia"
  forbidden:
    - "Inventar dados se cache vazio -- fallback 'sem registros' visível"
    - "Tocar src/mobile_cache/humor_heatmap.py (read-only -- já existe e funciona)"
  hipotese:
    - "humor_heatmap.py já gera cache .ouroboros/cache/humor-heatmap.json. UX-RD-17 só CONSOME esse cache + adiciona writer (escrever_humor.py)."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_be_hoje_humor.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "?cluster=Bem-estar&tab=Hoje -- hero esquerda (40px humor sliders) + coluna direita (3 mini-cards)"
    - "Hero: 4 sliders (humor/energia/ansiedade/foco) 1-5 + medicação toggle + horas sono input + chips multi-tag + textarea frase"
    - "Botão 'Registrar' grava daily/<YYYY-MM-DD>.md no vault, atualiza cache imediatamente"
    - "?cluster=Bem-estar&tab=Humor -- heatmap 13 sem × 7 dias, cells coloridas por humor médio (1=red, 5=green)"
    - "Overlay pessoa_a vs pessoa_b 50% opacity (mockup 18)"
    - "Stats 30d: média, dias registrados, máx, mín"
    - "Modal detalhe ao clicar cell"
    - "Vault inexistente: 'Vault não encontrado em <path>. Configure OUROBOROS_VAULT.' -- não crasheia"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # ?cluster=Bem-estar&tab=Hoje -- hero + 3 mini-cards
    # Registrar humor manual -> arquivo .md aparece em vault/daily/
    ls -la $(echo $OUROBOROS_VAULT)/daily/$(date +%F).md
    # ?cluster=Bem-estar&tab=Humor -- heatmap 13x7
    # screenshots vs 17 e 18
```

---

# Sprint UX-RD-17 — Bem-estar Hoje + Humor

**Status:** BACKLOG

Primeiras telas funcionais do cluster Bem-estar. **Read+Write** ao vault
(antes só read).

**Validação visual + funcional:** registrar humor manual no dashboard, conferir
que mobile lê o mesmo arquivo (Syncthing sincroniza). Esse é o teste de fogo
do bridge.

---

*"O dia bem registrado é o dia bem vivido." — princípio do diarismo*
