# CLAUDE.md

Este arquivo é auto-carregado pelo Claude Code ao abrir o projeto. Define o contexto canônico para qualquer nova sessão de Claude (Opus, Sonnet, etc.) trabalhar no protocolo-ouroboros.

## LEIA ANTES DE CRIAR QUALQUER SPRINT

1. `docs/sprints/ROADMAP_ATE_PROD.md` -- filosofia + 8 épicos canônicos + métricas globais
2. `docs/CICLO_GRADUACAO_OPERACIONAL.md` -- ritual artesanal de 6 fases
3. `contexto/COMO_AGIR.md` -- workflow canônico de 10 passos

## Filosofia em 3 linhas

O projeto chega em "prod" quando: dono joga arquivo em `inbox/`, roda `./run.sh --full-cycle`, e tudo aparece corretamente catalogado/categorizado/linkado sem revisão humana. Cada **tipo documental** percorre o ciclo de graduação (PENDENTE -> CALIBRANDO -> GRADUADO) onde o supervisor Opus principal lê amostras via Read multimodal, gera "prova dos 7" artesanal, e o ETL é confrontado contra ela 4-way (Opus x ETL x Grafo x Humano). 2 amostras concordantes graduam o tipo; daí o ETL processa autônomo.

## Ferramenta canônica de auditoria

`scripts/dossie_tipo.py` -- 7 subcomandos (abrir, listar-candidatos, prova-artesanal, comparar, graduar-se-pronto, snapshot, listar-tipos). Cada tipo tem dossiê persistente em `data/output/dossies/<tipo>/`.

## Comandos básicos

- `./run.sh --check` -- health check do ambiente
- `./run.sh --tudo` -- pipeline ETL completo
- `./run.sh --full-cycle` -- inbox + automações Opus + pipeline (recomendado para uso diário)
- `make smoke` -- 10 contratos aritméticos
- `make lint` -- ruff + check_acentuacao + cobertura D7
- `python -m pytest tests/ -q` -- suite completa (2975+ testes)
- `scripts/dossie_tipo.py listar-tipos` -- inventário dos 22 tipos documentais canônicos

## Regras invioláveis

- (b) Acentuação PT-BR completa em código/commits/docs (não, função, transação). Lint pega.
- (c) Zero emojis em qualquer artefato.
- (d) Zero menções a IA em commits e código.
- (e) `data/` em .gitignore -- PII nunca em log INFO.
- (g) Citação de filósofo no final de arquivo `.py` novo.

Padrões canônicos completos: `docs/PADROES_CANONICOS.md` (trackeado após META-VALIDATOR-BRIEF executar) ou `VALIDATOR_BRIEF.md` (local).
