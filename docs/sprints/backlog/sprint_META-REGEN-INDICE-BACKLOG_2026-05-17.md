---
id: META-REGEN-INDICE-BACKLOG <!-- noqa: accent -->
titulo: "Regenerar `INDICE_*.md` do backlog (130 specs reais vs 113 declaradas no índice 2026-05-12)" <!-- noqa: accent -->

status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-17
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 0.5
origem: "auditoria independente 2026-05-17. `docs/sprints/backlog/INDICE_2026-05-12.md` (último índice publicado) menciona 113 specs em backlog. Realidade hoje: 130 arquivos `.md` em `docs/sprints/backlog/`. Drift de 17 specs sem catalogação. Confunde próximo agente — abre o índice esperando navegar, mas não acha sprints recentes."
---

# Sprint META-REGEN-INDICE-BACKLOG <!-- noqa: accent -->


## Contexto

Índice canônico em `docs/sprints/backlog/INDICE_2026-05-12.md` desatualizado. Padrão atual:

- Documenta "113 specs em backlog" no header.
- Real `ls docs/sprints/backlog/*.md | wc -l` retorna 130.
- 17 specs criadas após 2026-05-12 sem catalogação (recentes: META-ROADMAP-METRICAS-AUTO, INFRA-DEDUP-NIVEL-2, etc).

Problema: índice serve como mapa para próximo Opus. Drift = confusão.

## Hipótese e validação ANTES

```bash
ls docs/sprints/backlog/INDICE_*.md
# Esperado: 1+ índices

wc -l docs/sprints/backlog/INDICE_2026-05-12.md
ls docs/sprints/backlog/*.md | wc -l
# Comparar contagem
```

## Objetivo

1. **Script `scripts/regenerar_indice_backlog.py`** (NOVO):
   - Lê todos `.md` em `docs/sprints/backlog/` (exceto `INDICE_*.md`).
   - Agrupa por épico (frontmatter `epico:` ou heurística por ID).
   - Gera `docs/sprints/backlog/INDICE_<YYYY-MM-DD>.md` com:
     - Header com data + count (`130 specs em 2026-05-17`)
     - Tabela por épico: ID, prioridade, esforço, status (BLOQUEADA marca)
     - Sub-grupos: "Onda atual", "Anti-débito (sprint-filha)", "Saneamento"
     - Link para spec antigo `INDICE_2026-05-12.md` movido para `_arquivado/`.

2. **Convenção canônica**:
   - Apenas 1 `INDICE_<data>.md` ativo. Anteriores arquivados em `docs/sprints/backlog/_arquivado/`.
   - `make sprints-indice` regenera.

3. **Validação**: cada spec tem `id:` no frontmatter (já existe). Sem `id:` → flag de spec malformada.

4. **Auditoria de specs órfãs** durante regeração:
   - Specs sem `epico:` no frontmatter → seção "Sem épico".
   - Specs com `status: concluída` em backlog/ (deveriam estar em concluidos/) → flag erro.
   - Specs duplicadas (mesmo ID com sufixo) → flag.

## Não-objetivos

- Não alterar specs (apenas catalogar).
- Não criar novos épicos (já temos 8 canônicos).
- Não tocar `docs/sprints/concluidos/`.

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/regenerar_indice_backlog.py
ls docs/sprints/backlog/INDICE_*.md
head -30 docs/sprints/backlog/INDICE_2026-05-17.md
# Esperado: indice novo com 130 specs catalogadas

mv docs/sprints/backlog/INDICE_2026-05-12.md docs/sprints/backlog/_arquivado/ 2>/dev/null
```

## Acceptance

- `scripts/regenerar_indice_backlog.py` criado.
- `docs/sprints/backlog/INDICE_2026-05-17.md` (130 specs).
- Índice antigo movido para `_arquivado/`.
- `make sprints-indice` adicionado ao Makefile.

## Padrões aplicáveis

- (l) Anti-débito — índice vivo evita drift.
- (kk) Sprint encerra com produto final — índice gerado e visível.

---

*"Índice desatualizado é mapa de outro reino." — princípio do catálogo vivo*
