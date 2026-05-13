---
id: META-SUPERVISOR-OPUS-ATUALIZAR
titulo: Reescrever docs/SUPERVISOR_OPUS.md citando ROADMAP + CICLO + dossie_tipo.py
status: backlog
concluida_em: null
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
