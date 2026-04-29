# Rodar Autônomo — Guia para sessão Opus orquestrar agentes em sequência

> Documento canônico para uma nova sessão Opus que vai rodar agentes (planejador → executor → validador) iterativamente até completar o plan `pure-swinging-mitten`. Lê na ordem; respeita os pontos de intervenção humana.

## 1. Onboarding obrigatório (cole no início da sessão)

```
Voce eh o supervisor Opus do protocolo-ouroboros. Vai executar o plan
pure-swinging-mitten orquestrando agentes (planejador-sprint, executor-sprint,
validador-sprint) ate completar todas as ondas OU ate atingir um ponto de
intervencao humana documentado em docs/RODAR_AUTONOMO.md secao 4.

Antes de qualquer acao, leia exatamente nesta ordem:

1. contexto/POR_QUE.md
2. contexto/ESTADO_ATUAL.md
3. contexto/COMO_AGIR.md
4. CLAUDE.md (constituicao tecnica)
5. ~/.claude/plans/pure-swinging-mitten.md (plan ativo)
6. docs/SPRINTS_INDEX.md (indice mestre + ordem)
7. docs/RODAR_AUTONOMO.md (este documento)
8. VALIDATOR_BRIEF.md (rodape: padroes canonicos)

Confirme com 1 frase o estado atual e propunha a primeira sprint conforme
a ordem em SPRINTS_INDEX.md secao "Ordem de execucao recomendada".
Use AskUserQuestion APENAS nos pontos de intervencao listados em
RODAR_AUTONOMO.md secao 4.
```

## 2. Loop canônico por sprint (workflow tripla validação)

Para cada sprint do backlog (em ordem de Onda):

```
[ANTES — fase preventiva]
  1. Ler spec em docs/sprints/backlog/<arquivo>.md
  2. Ler ADRs referenciados
  3. grep para validar a hipotese da spec
  4. Se hipotese contraditada: REPROVAR a spec + escrever achado-bloqueio + AskUserQuestion
  5. make lint && make smoke && pytest -q (estado verde antes de mexer)
  6. Capturar baseline pytest

[DURANTE — fase contínua]
  7. Despachar agente executor-sprint com a spec
  8. Aguardar entrega
  9. Validar 2-3 claims-chave do agente (NAO aceitar cego)
  10. Se claims falham: re-despachar com patch-brief

[DEPOIS — fase de fechamento, gate anti-migue 9 checks]
  11. Hipotese validada com grep (registro)
  12. Proof-of-work runtime real (log capturado)
  13. Se aplicavel: make conformance-<tipo> exit 0 (>=3 amostras 4-way)
  14. make lint exit 0
  15. make smoke 10/10 contratos
  16. pytest baseline mantida ou crescida
  17. Achados colaterais: sprint-ID OU Edit-pronto (zero TODO)
  18. Despachar validador-sprint OU validar pessoalmente
  19. Spec movida para concluidos/ com `concluida_em: YYYY-MM-DD` e link commit

[GIT]
  20. Commit atomico PT-BR imperativa, sem mencao a IA
  21. AskUserQuestion para autorizar push
```

## 3. Ordem de execução (dependências cruzadas)

Definida em `docs/SPRINTS_INDEX.md` secao "Ordem de execução recomendada".
Resumo crítico:

```
Onda 0 (PRÉ-REQUISITO ABSOLUTO):
  - DESIGN-01 (P0)  — blueprint de outputs
  - CI-01      (P0) — corrigir CI (bugs criticos)
  > Sem isso, restante roda mas falsa seguranca

Onda 1 (anti-migue + restaurar debitos):
  - ANTI-MIGUE-01 (P0) — gate 4-way conformance — BLOQUEANTE para Onda 3
  - ANTI-MIGUE-05/06 — restaurar Sprint 87/87d
  - ANTI-MIGUE-08 — refatorar arquivos > 800 linhas
  - ANTI-MIGUE-09/10/11/12 — higiene
  - MAKE-AM-01 — make anti-migue target

Onda 2 (LLM):
  - LLM-01 (P0) — infra Anthropic (BLOQUEANTE para Onda 3 LLM-driven)
  - LLM-02..07 — supervisor + auditor + metricas
  - AUDITOR-01 — relatorio cobertura por pessoa

Onda 3 (cobertura documental):
  - 20 sprints DOC-01..20 + OCR-AUDIT-01 + TEST-AUDIT-01
  - Cada extrator novo passa por gate 4-way (ANTI-MIGUE-01)
  - Pode rodar paralelo em ondas de 5 sprints

Onda 4 (cruzamento + IRPF):
  - LINK-AUDIT-01 (P0) — fix vinculacao das/boleto/nfce
  - MICRO-01..03 + IRPF-01..02 + GAP-01 + GRAFO-XLSX-01

Onda 5 (mobile + fontes):
  - MOB-01..03 + FONTE-01..04
  - Pode rodar paralelo a Onda 3-4

Onda 6 (UX + OMEGA):
  - UX-01..10 + OMEGA-94a..d + ADR-23 + MON-01 + DASH-01
```

## 4. Pontos de intervenção humana (NÃO autônomo)

A sessão Opus DEVE pausar via AskUserQuestion nos seguintes pontos. Sem
intervenção humana, nenhuma das 7 sprints abaixo pode fechar.

| Sprint | O que precisa do humano |
|---|---|
| **DESIGN-01** | Aprovar blueprint de outputs/relatórios; decidir formato canônico |
| **CI-01** | Validar que badge no README é apropriado; aprovar push do .github/workflows/ |
| **ANTI-MIGUE-01** | Implementar gate, mas **marcar manualmente as ≥3 amostras 4-way** (humano-no-loop) |
| **LLM-01** | Configurar `ANTHROPIC_API_KEY` em `.env` local |
| **DOC-01..20** (cada um) | Marcar amostras 4-way no Revisor visual antes do gate fechar |
| **FONTE-01** | OAuth Google Calendar (browser interativo) |
| **FONTE-02** | Path do perfil Thunderbird local pode variar |
| **ADR-23-DRAFT** | Decisão arquitetural envelope vs pessoa como path canônico |
| **MOB-01/02/03** | Coordenação com desenvolvimento separado de Mob-Ouroboros |

Padrão: ao chegar nesses pontos, Opus para, lista o que precisa, AskUserQuestion
clara, espera resposta humana, prossegue.

## 5. Sinais de parada de emergência

Sessão Opus DEVE parar e avisar o humano se detectar:

- `make smoke` quebra (regressão em contrato aritmético).
- `pytest` baseline cai (regressão em testes existentes).
- `make lint` exit não-zero por mais de 2 tentativas consecutivas.
- Sprint atual depende de outra ainda não-fechada (loop de dependência).
- Achado P0 colateral durante execução que invalida hipótese da spec.
- 3 sprints consecutivas REPROVADAS pelo validador (suspeita de bug sistêmico).

## 6. Métricas de progresso

Sessão deve reportar a cada 5 sprints:

```
[PROGRESSO]
- Sprints fechadas nesta sessao: N
- Sprints pendentes na Onda atual: M
- pytest baseline: X (delta +Y desde inicio)
- smoke: 10/10
- lint: exit 0
- conformance: K tipos com gate 4-way verde
- Pontos de intervencao humana proximos: <lista>
```

## 7. Estimativa de duração

Plan completo: **~200h** (170h plan + 27h sprints novas + 3h buffer).

- Sessão Opus pode fechar 2-3 sprints/h em condições ideais (sprints pequenas).
- Sprints com gate 4-way demoram mais (precisam de 3 amostras + revisão humana).
- Estimativa realista: **8-12 sessões de 4-6h cada** em ritmo sustentável, ou **3-4 sessões maratona de 12-16h** se humano se compromete a estar disponível para validar gates.

## 8. Resposta direta à pergunta "está tudo certo?"

**Sim, com 4 caveats explícitos:**

1. **DESIGN-01 e CI-01 são P0 bloqueantes** — sem isso, autônomo dá falsa segurança (Onda 0).
2. **ANTI-MIGUE-01 (gate 4-way) precisa de humano marcando amostras** — não dá pra automatizar 100%.
3. **LLM-01 precisa de ANTHROPIC_API_KEY** — humano configura uma vez.
4. **FONTE-01/02 precisam de credenciais externas** — humano configura quando chegar.

Fora esses 4 pontos, **uma sessão Opus pode rodar autônoma do começo ao fim** seguindo o loop canônico desta seção 2 + ordem da seção 3, parando apenas nos pontos de seção 4.

---

*"Autonomia não é ausência de humano — é humano sabendo onde precisa estar." — princípio do orquestrador disciplinado*
