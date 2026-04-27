## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-110
  title: "Busca Global como primeira aba do cluster Documentos"
  prioridade: P1
  estimativa: 30min
  origem: "feedback dono 2026-04-27 -- Busca Global é o ponto de entrada cognitivo do cluster, não pode ser a 4a aba"
  pre_requisito_de: [100]
  touches:
    - path: src/dashboard/app.py
      reason: "reordenar ABAS_POR_CLUSTER['Documentos'] e a chamada st.tabs() correspondente"
    - path: tests/test_dashboard_deeplink_tab.py
      reason: "atualizar teste de invariante 1:1 com nova ordem"
  forbidden:
    - "Mudar nomes das abas (so a ordem)"
    - "Reordenar outros clusters"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_deeplink_tab.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "ABAS_POR_CLUSTER['Documentos'] = ['Busca Global', 'Catalogação', 'Completude', 'Revisor', 'Grafo + Obsidian']"
    - "Chamada st.tabs() em main() respeita exatamente essa ordem"
    - "Sprint 100 deep-link continua: ?cluster=Documentos abre 'Busca Global' como tab default (sem ?tab=)"
    - "Testes existentes da Sprint 100 atualizados para nova ordem; nenhuma regressao"
  proof_of_work_esperado: |
    # Antes
    grep -A 6 "Documentos" src/dashboard/app.py | head -10
    # = ordem ['Catalogacao', 'Completude', 'Revisor', 'Busca Global', 'Grafo + Obsidian']

    # Depois
    [mesmo grep]
    # = ordem ['Busca Global', 'Catalogacao', 'Completude', 'Revisor', 'Grafo + Obsidian']

    # Probe runtime (Playwright):
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # Abrir http://localhost:8520/?cluster=Documentos (sem ?tab=)
    # Esperado: 'Busca Global' renderizada como tab default
```

---

# Sprint UX-110 -- Busca Global como primeira aba

**Status:** CONCLUÍDA (commit `61464e4`, mergeada em main como `2bf61dc`, 2026-04-27 — aguarda validação visual humana)

Mudança cirúrgica de ordem. Hoje cluster Documentos abre em "Catalogação"; deve abrir em "Busca Global" porque a busca é o ponto de entrada cognitivo.

---

*"Onde o usuário chega primeiro define o que ele vai entender que o sistema faz." -- princípio do default semântico*
