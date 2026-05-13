# Prompt canônico para nova sessão Claude Code no protocolo-ouroboros

Versão pública (sem PII). Para a versão pessoal com contexto familiar e bancário
do dono, ver `contexto/PROMPT_NOVA_SESSAO.md` (gitignored, fica apenas na máquina
do supervisor).

Este arquivo viaja com o repositório. Em máquina nova ou clone limpo, basta abrir
o projeto no Claude Code e seguir a ordem de leitura abaixo. A constituição
técnica (`CLAUDE.md`) é auto-carregada pelo harness; os demais documentos
oferecem profundidade conforme a tarefa exige.

## Leitura obrigatória (nesta ordem)

1. `CLAUDE.md` (raiz) -- auto-carregado pelo harness; resume tudo abaixo.
2. `docs/sprints/ROADMAP_ATE_PROD.md` -- filosofia + 8 épicos canônicos + métricas globais.
3. `docs/CICLO_GRADUACAO_OPERACIONAL.md` -- ritual artesanal de 6 fases para graduar tipo documental.
4. `contexto/COMO_AGIR.md` -- workflow canônico de 10 passos (whitelist do `contexto/`).
5. `docs/PADROES_CANONICOS.md` -- padrões empíricos `(a)..(ll)` destilados de incidentes.

Complementos para tarefas específicas:

- `docs/SUPERVISOR_OPUS.md` -- manifesto do papel do supervisor Opus principal.
- `contexto/ESTADO_ATUAL.md` -- snapshot da rodada corrente.
- `contexto/PROTOCOLO_ANTI_ARMADILHA_V3_1.md` -- comandos git banidos, isolamento de worktree.
- `VALIDATOR_BRIEF.md` (local) -- mesmos padrões `(a)..(ll)` em formato de checklist.

## Filosofia em 3 linhas

O projeto chega em prod quando: o dono joga arquivo em `inbox/`, roda
`./run.sh --full-cycle`, e tudo aparece corretamente catalogado, categorizado e
linkado sem revisão humana. Cada **tipo documental** percorre o ciclo de
graduação (PENDENTE -> CALIBRANDO -> GRADUADO) onde o supervisor Opus principal
lê amostras via Read multimodal, gera a prova artesanal, e o ETL é confrontado
contra ela em modo 4-way (Opus x ETL x Grafo x Humano). Duas amostras
concordantes graduam o tipo; daí o ETL processa autônomo.

## Comandos canônicos

Pipeline e diagnóstico:

- `./run.sh --check` -- health check do ambiente.
- `./run.sh --tudo` -- pipeline ETL completo.
- `./run.sh --full-cycle` -- inbox + automações Opus + pipeline (uso diário).

Auditoria por tipo documental (ferramenta canônica do ciclo de graduação):

- `python3 scripts/dossie_tipo.py listar-tipos` -- inventário dos 22 tipos canônicos.
- `python3 scripts/dossie_tipo.py snapshot` -- regenera `graduacao_tipos.json` global.
- `python3 scripts/dossie_tipo.py abrir <tipo>` -- estado do dossiê de um tipo.
- `python3 scripts/dossie_tipo.py listar-candidatos <tipo>` -- arquivos candidatos.
- `python3 scripts/dossie_tipo.py prova-artesanal <tipo> <sha256>` -- stub para supervisor preencher.
- `python3 scripts/dossie_tipo.py comparar <tipo> <sha256>` -- confronto prova vs ETL.
- `python3 scripts/dossie_tipo.py graduar-se-pronto <tipo>` -- avalia transição de status.

Gauntlet de qualidade:

- `make smoke` -- 10 contratos aritméticos.
- `make lint` -- ruff + check_acentuacao + cobertura D7.
- `python -m pytest tests/ -q` -- suíte completa (2975+ testes).

## Workflow para sprint nova

Caminho curto (detalhe completo em `contexto/COMO_AGIR.md`):

1. Ler `docs/sprints/ROADMAP_ATE_PROD.md` e identificar o épico.
2. Se a sprint toca tipo documental, fazer prova artesanal ANTES de despachar
   executor (padrão `(jj)`): `dossie_tipo.py prova-artesanal <tipo> <sha256>`.
3. Validar hipótese da spec com `grep` antes de codar (padrão `(k)`).
4. Despachar executor com escopo fechado (touches autorizados explícitos).
5. Encerrar a sprint apenas quando `dossie_tipo.py comparar` retorna
   `GRADUADO_OK` (padrão `(kk)`); divergência abre sprint-filha automática.

## Documentos canônicos do projeto (mapa)

| Arquivo | Função |
|---|---|
| `CLAUDE.md` | constituição técnica (auto-carregada) |
| `docs/sprints/ROADMAP_ATE_PROD.md` | mapa de 8 épicos canônicos |
| `docs/CICLO_GRADUACAO_OPERACIONAL.md` | ritual artesanal de 6 fases |
| `contexto/COMO_AGIR.md` | workflow operacional de 10 passos |
| `docs/PADROES_CANONICOS.md` | padrões empíricos `(a)..(ll)` |
| `docs/SUPERVISOR_OPUS.md` | manifesto do papel do supervisor |
| `docs/PROMPT_NOVA_SESSAO.md` | meta-onboarding público (este arquivo) |
| `VALIDATOR_BRIEF.md` | padrões `(a)..(ll)` em checklist (local) |
| `contexto/PROTOCOLO_ANTI_ARMADILHA_V3_1.md` | disciplina de worktree + comandos banidos |

## Regras invioláveis (resumo)

- `(b)` Acentuação PT-BR completa em código, commits e docs (não, função, transação). Lint pega.
- `(c)` Zero emojis em qualquer artefato.
- `(d)` Zero menções a nomes de modelos ou fabricantes em commits e código.
- `(e)` `data/` em `.gitignore`; PII jamais em log INFO.
- `(g)` Citação de filósofo no final de arquivo `.py` novo.

Lista completa: `docs/PADROES_CANONICOS.md`.

## Validação PII (acceptance deste arquivo)

Este arquivo NÃO pode conter:

- CPF ou CNPJ real.
- Nome completo de pessoa física.
- Número de conta bancária.
- Outro dado sensível identificável.

A versão com PII vive em `contexto/PROMPT_NOVA_SESSAO.md` (gitignored, fica
apenas na máquina do supervisor).

---

*"Onboarding público viaja com o repo; onboarding privado fica em casa." -- princípio da clivagem*
