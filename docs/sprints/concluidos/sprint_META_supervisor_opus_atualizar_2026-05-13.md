---
id: META-SUPERVISOR-OPUS-ATUALIZAR
titulo: Reescrever docs/SUPERVISOR_OPUS.md citando ROADMAP + CICLO + dossie_tipo.py
status: concluída
concluida_em: 2026-05-13
prioridade: P0
data_criacao: 2026-05-13
fase: SANEAMENTO
epico: 8
depende_de:
  - META-ONBOARDING-NOVA-SESSAO (preferível antes)
origem: auditoria de discoverability 2026-05-13. docs/SUPERVISOR_OPUS.md é o manifesto canônico do papel do supervisor mas grep não encontra menções a ROADMAP, CICLO_GRADUACAO ou dossie_tipo.py. Doc desatualizado em relação à infra atual.
---

# Sprint META-SUPERVISOR-OPUS-ATUALIZAR

## Contexto

`docs/SUPERVISOR_OPUS.md` (trackeado) descreve o papel do supervisor Opus principal. Foi escrito antes da infra atual (ROADMAP + CICLO + dossiê). Não menciona:
- Os 8 épicos canônicos do roadmap
- O ritual de 6 fases do ciclo de graduação
- A ferramenta `scripts/dossie_tipo.py`
- Os padrões (jj)(kk)(ll) novos

Próxima sessão lendo este doc fica com modelo mental desatualizado.

## Entregável

Reescrita do `docs/SUPERVISOR_OPUS.md`:

1. **Seção "Antes de qualquer sprint"** -- exigir leitura de ROADMAP + CICLO + COMO_AGIR.
2. **Seção "Ritual artesanal"** -- explicar as 6 fases com link para CICLO_GRADUACAO_OPERACIONAL.md.
3. **Seção "Ferramenta canônica de auditoria"** -- documentar `dossie_tipo.py` e suas 7 subcomandos.
4. **Seção "Como sprint encerra"** -- padrão (kk): produto final imediato, sem fechamento posterior.
5. Preservar seções históricas (papel do supervisor vs executor, despacho em paralelo, etc.).

## Acceptance

- `grep -l "ROADMAP_ATE_PROD\|CICLO_GRADUACAO\|dossie_tipo" docs/SUPERVISOR_OPUS.md` retorna o arquivo.
- Seções listadas acima existem.
- Doc continua com tamanho razoável (não infla mais de 30% sobre versão original).
- Lint zero.

## Padrão canônico aplicável

(v) Spec retroativa -- doc canônico desatualizado é forma de spec retroativa não escrita.

---

*"Manifesto que não cita a ferramenta vira ornamento." -- princípio do doc vivo*

---

## Conclusão (2026-05-13)

Reescrita aplicada em `docs/SUPERVISOR_OPUS.md` (346 → 430 linhas, +24%, dentro do limite +30%):

- **§0 — Antes de qualquer sprint** (nova): exige leitura de `ROADMAP_ATE_PROD.md` + `CICLO_GRADUACAO_OPERACIONAL.md` + `contexto/COMO_AGIR.md`. Lista os 8 épicos canônicos. Aponta para dossiês em `data/output/dossies/<tipo>/`.
- **§2.5 — Ritual artesanal (6 fases)** (nova): resumo de 1 linha por fase, com link para `CICLO_GRADUACAO_OPERACIONAL.md`. Marca fases 3 e 5 como exclusivas do Opus principal (Read multimodal independente para gabarito).
- **§3.5 — Ferramenta canônica de auditoria** (nova): tabela com os 7 subcomandos de `scripts/dossie_tipo.py` (`abrir`, `listar-candidatos`, `prova-artesanal`, `comparar`, `graduar-se-pronto`, `snapshot`, `listar-tipos`) e estrutura do dossiê.
- **§3.6 — Como sprint encerra (padrão (kk))** (nova): sprint de tipo documental encerra com `comparar` retornando `GRADUADO_OK` (ou `DIVERGENTE` com sprint-filha automática); não há fechamento posterior.
- **§6** (atualizada): adiciona `ROADMAP_ATE_PROD.md` e `CICLO_GRADUACAO_OPERACIONAL.md` na ordem de leitura pós-queda. Rodapé do BRIEF agora vai até `(ll)` (não mais `(cc)`).
- **§8** (atualizada): inclui `(ii)`, `(jj)`, `(kk)`, `(ll)`; corrige `(z)` (spec retroativa → `(v)`; gate 4-way → `(z)`).

### Acceptance verificado

- `grep -c "ROADMAP\|CICLO_GRADUACAO\|dossie_tipo" docs/SUPERVISOR_OPUS.md` → 18 (antes: 0).
- Tamanho final: 430 linhas (+24% sobre 346 originais, dentro do limite +30%).
- `make lint` exit 0.
- `make smoke` 23/23 checagens, 0 erros.
- `git stash list`: 3 stashes pré-existentes de executores anteriores (não criados por esta sprint; protocolo v3.1 proíbe drop de stash alheio).

### Diff stats

```
docs/SUPERVISOR_OPUS.md | 94 +++++++++++++++++++++++++++++++++++++--
1 file changed, 88 insertions(+), 6 deletions(-)
```

### Padrões aplicados

- `(v)` Spec retroativa não escrita — doc canônico desatualizado virou spec viva.
- `(a)` Edit incremental, não rewrite — preservadas todas as seções existentes.
- `(b)` Acentuação PT-BR completa nas adições.
- `(ii)` Comandos git banidos respeitados — sem `stash`, `reset --hard`, `clean -fd`.
