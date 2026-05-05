---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-16
  title: "Bridge vault Bem-estar: estender src/mobile_cache/ para 9 schemas YAML"
  prioridade: P0
  estimativa: 4h
  onda: 6
  origem: "docs/MAPA_FEATURES_MOBILE_DESKTOP.md §3 (18 schemas YAML mobile) + reuso de humor_heatmap.py"
  bloqueia: [UX-RD-17, UX-RD-18, UX-RD-19]
  depende_de: [UX-RD-03, MOB-bridge-3]
  touches:
    - path: src/mobile_cache/diario_emocional.py
      reason: "NOVO -- parser frontmatter + body, gera .ouroboros/cache/diario-emocional.json. Reusa _ler_frontmatter de humor_heatmap.py"
    - path: src/mobile_cache/eventos.py
      reason: "NOVO -- parser eventos com geo (lugar, bairro), categoria, fotos refs"
    - path: src/mobile_cache/treinos.py
      reason: "NOVO -- parser treino_sessao com exercicios refs"
    - path: src/mobile_cache/medidas.py
      reason: "NOVO -- parser medidas (peso, cintura, etc) + fotos comparativas"
    - path: src/mobile_cache/marcos.py
      reason: "NOVO -- parser marcos (manuais + auto-gerados)"
    - path: src/mobile_cache/alarmes.py
      reason: "NOVO -- parser alarmes com recorrência"
    - path: src/mobile_cache/contadores.py
      reason: "NOVO -- parser contadores 'Dias sem X'"
    - path: src/mobile_cache/ciclo.py
      reason: "NOVO -- parser ciclo_menstrual com fases"
    - path: src/mobile_cache/tarefas.py
      reason: "NOVO -- parser tarefas leve"
    - path: src/mobile_cache/varrer_vault.py
      reason: "NOVO -- entrypoint que invoca todos 9 parsers + humor_heatmap; CLI: python -m src.mobile_cache.varrer_vault [--vault-root <path>]"
    - path: scripts/smoke_bem_estar.py
      reason: "NOVO -- smoke aritmético do cluster Bem-estar (contagem cache vs filesystem)"
    - path: tests/test_mobile_cache_bem_estar.py
      reason: "NOVO -- 18 testes (2 por parser): parsing de fixture + cache JSON gerado correto"
  forbidden:
    - "Reescrever humor_heatmap.py -- só REUSAR helpers (_ler_frontmatter, _normalizar_data, _coerce_int)"
    - "Hardcodar vault path -- parametrizar via Path(os.path.expanduser('~/Protocolo-Ouroboros')) ou variável OUROBOROS_VAULT"
    - "Ler vault em caminho que não existe e crashar -- fallback graceful com aviso"
  hipotese:
    - "src/mobile_cache/humor_heatmap.py exporta _ler_frontmatter, _normalizar_data, _coerce_int. Confirmar via grep."
    - "Vault desktop está em ~/Protocolo-Ouroboros (Sprint 70 / sync_rico) OU em path Syncthing-mapped diferente. Pré-requisito: AskUserQuestion ao dono no início da execução para confirmar path."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_mobile_cache_bem_estar.py -v"
    - cmd: ".venv/bin/python -m src.mobile_cache.varrer_vault --vault-root tests/fixtures/vault_sintetico/"
    - cmd: ".venv/bin/python scripts/smoke_bem_estar.py"
    - cmd: "make smoke"
  acceptance_criteria:
    - "9 parsers em src/mobile_cache/ (excluindo humor_heatmap.py que já existe)"
    - "Cada parser exporta varrer(vault_root) -> dict; e cli (python -m src.mobile_cache.<schema>)"
    - "Cache em .ouroboros/cache/<schema>.json com formato {gerado_em, vault_root, items: [...]}"
    - "varrer_vault.py invoca todos 9 + humor_heatmap; loga progresso"
    - "Reusa _ler_frontmatter de humor_heatmap.py (grep mostra import)"
    - "Fixture vault_sintetico em tests/fixtures/ com pelo menos 2 arquivos por schema"
    - "smoke_bem_estar.py compara count(cache) == count(filesystem) por schema, falha se desigual"
    - "pytest baseline mantida + 18 testes novos"
    - "Vault path inexistente NÃO crasheia: aviso e cache vazio"
  proof_of_work_esperado: |
    # Hipótese: helpers reutilizáveis
    grep -n "_ler_frontmatter\|_normalizar_data\|_coerce_int" src/mobile_cache/humor_heatmap.py
    # esperado: declarações em humor_heatmap

    # AC: varredura de fixture
    .venv/bin/python -m src.mobile_cache.varrer_vault --vault-root tests/fixtures/vault_sintetico/
    ls .ouroboros/cache/
    # esperado: 10 JSONs (humor + 9 novos)

    # AC: reuso (cada parser importa helpers)
    grep -l "from src.mobile_cache.humor_heatmap import" src/mobile_cache/*.py | wc -l
    # esperado: >= 5

    # AC: smoke
    .venv/bin/python scripts/smoke_bem_estar.py
    # = OK 9/9 schemas
```

---

# Sprint UX-RD-16 — Bridge vault Bem-estar

**Status:** BACKLOG

Sprint **fundação** da Onda 6. Sem ela, as 3 sprints de telas Bem-estar
(UX-RD-17/18/19) não têm dados.

**Pré-requisito interativo (`AskUserQuestion` no início):** o dono precisa
confirmar o caminho real do vault Bem-estar no desktop. Se Syncthing não
estiver configurado, sprint vira "instalar Syncthing + sync vault" antes
do parser. Não pode chutar.

**Por quê não-visual:** essa é a única sprint Onda 6 que não toca UI. Tudo
backend (parsers + cache + smoke). Validação é via CLI + smoke.

**Specs absorvidas:** parte de Sprint 94 (fusão vault Ouroboros — backlog
histórico) — fica pendente, mas UX-RD-16 entrega bridge mínimo viável para
Bem-estar.

---

*"Sem fundação, o castelo é só desenho." — princípio da engenharia*
