# COMO_AGIR.md -- Workflow operacional para o Opus

> Este arquivo te diz como agir, nao apenas o que voce pode fazer. Le com atencao -- a ordem dos passos importa.

## Hierarquia de instrucoes (atualizada 2026-04-29 pela DOC-VERDADE-01.B)

Quando duas regras conflitarem, a ordem de precedencia eh:

1. **Instrucao explicita do dono humano (mensagem direta)** -- prioridade maxima.
2. **ADRs aceitas em `docs/adr/`** -- decisoes arquiteturais canonicas (ex: ADR-13 sobre supervisor sem API; ADR-08 sobre ciclo Supervisor-Aprovador). Vencem CLAUDE.md em qualquer caso de conflito estrutural.
3. **CLAUDE.md** -- constituicao tecnica do projeto (regras inviolaveis e workflow).
4. **`docs/SUPERVISOR_OPUS.md`** -- manifesto canonico do papel do supervisor (Opus interativo).
5. **`VALIDATOR_BRIEF.md`** -- padroes canonicos descobertos em sprints anteriores. Eh historico-cumulativo (nao regra rigida); pode evoluir.
6. **`~/.claude/plans/<slug>.md`** -- plan ativo (aspiracao de fechamento, NAO eh verdade do estado atual).
7. **`docs/PLANOS_SESSAO/<data>_<slug>.md`** -- snapshot versionado de planos em curso (preserva conhecimento entre sessoes).
8. **Spec da sprint** que voce esta executando -- escopo declarado.
9. **Skills do Claude Code** (sprint-ciclo, validar-sprint, propor-extrator, auditar-cobertura, etc).
10. **Default do sistema**.

Se a spec contradiz CLAUDE.md ou ADR, voce REPROVA a spec antes de executar.

### Quando fontes divergem (regras canonicas)

- **ADRs vencem CLAUDE.md** em qualquer decisao estrutural. Se ADR diz "nao implementar X" e CLAUDE.md tem trecho que poderia ser lido como "implementar X", ADR vence. CLAUDE.md deve ser corrigido na proxima oportunidade (sprint META-* ou similar).
- **Plan ativo eh aspiracao, nao verdade**. Se o plan diz "Sprint Y a fazer" mas `git log` mostra Sprint Y commitada, o git log ganha. Auditar via `python scripts/auditar_estado.py` se desconfiar.
- **VALIDATOR_BRIEF eh padrao descoberto, nao regra**. Pode evoluir; padroes (a..cc) sao recomendacoes empiricas, nao mandamentos.
- **`docs/PLANOS_SESSAO/` mostra o que esta em curso AGORA**. Se voce assumiu sessao apos queda do Opus anterior, leia este diretorio antes de qualquer coisa para entender o que estava sendo feito.
- **Sempre que possivel: confie no codigo, nao na doc**. Verdade vivo eh `git log` + `ls docs/sprints/concluidos/` + comportamento em runtime. Doc eh fotografia.

## 4 modos de operacao

### Modo 1 -- LEITURA / DIAGNOSTICO (read-only, sem efeito colateral)

Quando: usuario pede "audita", "le", "explica", "investiga".

Faca:
- Use `Read`, `Grep`, `Glob`, `Bash` (com comandos read-only).
- Pode rodar `make smoke`, `pytest`, `git status`, `git log`, mas NAO `./run.sh --tudo` que regenera XLSX.
- Pode despachar agentes em background.
- **Nunca edite, escreva, mova, delete.**

### Modo 2 -- PLANO (plan mode ativo)

Quando: usuario invoca plan mode OU pede "me proponha um plano".

Faca:
- 5 fases: entender -> design -> revisar -> escrever plano -> ExitPlanMode.
- Use AskUserQuestion para clarificar ambiguidades (3-4 perguntas, multiSelect quando aplicavel).
- Escreva o plano em `~/.claude/plans/<slug>.md`.
- **Nao edite codigo. Nao escreva fora do plano.** Excecao: pode usar TaskCreate para registrar tasks internas.

### Modo 3 -- EXECUCAO (commit a commit, supervisionado)

Quando: usuario aprovou um plano OU pediu "executa Sprint NN".

Faca para cada sprint:
1. Ler spec completa em `docs/sprints/backlog/sprint_<NN>_*.md`.
2. Ler ADRs referenciados.
3. Validar hipotese com `grep` antes de aplicar fix (CLAUDE.md regra empirica).
4. Implementar.
5. Rodar testes locais da area (`pytest tests/test_<area>.py`).
6. Rodar `make lint` + `make smoke`.
7. Commit atomico com mensagem PT-BR imperativa, **SEM mencao a IA**.
8. Aguardar aprovacao do dono para `git push`.
9. Quando aprovado, mover spec para `docs/sprints/concluidos/`.

### Modo 4 -- VALIDACAO (subagente validador)

Quando: usuario invoca skill `validar-sprint` ou pede "valida o que esta feito".

Faca:
- Roda `make lint` + `make smoke` + pytest area.
- Le diff completo do commit.
- Confere acentuacao em arquivos perifericos (citacao filosofo, docstrings, comentarios).
- Confirma que cada acceptance criteria foi atendido (proof-of-work runtime).
- Se UI tocada, invoca skill `validacao-visual` (3 tentativas: scrot -> claude-in-chrome -> playwright).
- Reporta: APROVADO / APROVADO_COM_RESSALVAS / REPROVADO + patch-brief se REPROVADO.

## Quando despachar agente em background

**Despache** quando:
- Tarefa eh independente e pesada (>5 min).
- Voce pode trabalhar em outra coisa enquanto roda.
- O resultado eh facilmente verificavel por amostragem (claims explicitos).

**NAO despache** quando:
- Voce precisa do resultado para o proximo passo imediato.
- A tarefa eh pequena (<2 min).
- O resultado mistura interpretacao subjetiva (ex: "qual a melhor abordagem?").

**Apos receber a entrega:**
1. Leia o sumario do agente.
2. Pegue 2-3 claims-chave (ex: "X tem N arquivos", "Y arquivo contem texto Z").
3. Valide cada claim com bash/grep.
4. Se 100% bater -> aceitar.
5. Se 1+ falhar -> rejeitar a entrega e re-despachar com prompt mais especifico.

Padrao usado em 2026-04-26: "agente do vault" entregou 7 claims, validei 5 (todos OK). "Agente do ETL" entregou 8 claims, validei 2 (todos OK). Aceitei ambos.

## Workflow de sprint completa (Mode 3 detalhado)

```
1. Skill /sprint-ciclo NN   (ou execucao manual)
   ↓
2. Ler spec + ADRs + VALIDATOR_BRIEF rodape
   ↓
3. PLANO: usar AskUserQuestion para ambiguidades
   ↓
4. EXECUTAR:
   a. Validar hipotese com grep (NAO IGNORAR)
   b. Implementar mudancas em src/
   c. Adicionar testes em tests/
   d. make lint + make smoke + pytest tests/test_<area>.py
   e. Se vermelho, fixar e voltar a (d)
   f. git add . && git commit -m "tipo: descricao em PT-BR"
   ↓
5. VALIDAR (se executou em paralelo, eh outro agente):
   a. APROVADO: move spec para concluidos/, atualiza VALIDATOR_BRIEF rodape
   b. APROVADO_COM_RESSALVAS: cada ressalva vira sprint-filha em backlog/
   c. REPROVADO: patch-brief para executor + replan
   ↓
6. AGUARDAR aprovacao do dono para push
   ↓
7. git push (ou abrir PR via /commit-push-pr)
```

## Quando perguntar vs quando agir

**Pergunte ANTES de agir:**
- Operacao destrutiva (rm -rf, git reset --hard, force push, deletar branch).
- Decisao arquitetural nao-obvia (mudar schema, criar ADR, mover modulo).
- Acao visivel a outros (push para main, PR para upstream, comment GitHub).
- Voce nao tem contexto suficiente para escolher entre 2+ opcoes.

**Aja sem perguntar:**
- Edicao local de codigo dentro do escopo da spec.
- Adicao de teste regressivo.
- Renomeacao interna se claramente alinhada com convencao.
- Atualizacao de docstrings, comentarios.
- Lint/format.

**Sempre confirme push:**
- `git push` mesmo em branch feature.
- `gh pr create`.
- `gh pr merge`.

## Padroes de commit

### Mensagem
- PT-BR imperativa.
- Tipo + dois pontos + descricao.
- Tipos: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
- Maximo 70 caracteres na primeira linha.
- Corpo (opcional) com WHY, nao WHAT.
- **NUNCA** mencionar Claude, GPT, Anthropic, IA. Hook commit-msg bloqueia.

Exemplo:
```
fix(sprint 95): linking documento->transacao em runtime real

Motor da Sprint 48 era invocado mas nao produzia arestas.
Causa: tolerancia temporal de 3 dias estava muito apertada.
Ampliado para 14 dias. 41 docs -> 32 vinculados (78%).

```

### Quando NAO commitar (ainda)
- Lint vermelho.
- Pytest em vermelho na area afetada.
- Smoke aritmetico quebrou.
- Acentuacao quebrada em arquivo periferico.
- Spec ainda em backlog/ (tem que mover para concluidos/ na mesma rodada).

## Validacao visual (UI)

Quando o diff toca dashboard, Streamlit, HTML, CSS, ou template:

1. Skill `validacao-visual` eh **auto-invocada** pelo validador-sprint.
2. Pipeline 3 tentativas:
   a. CLI X11 (scrot, import, xdotool) -- pre-autorizado em settings.json.
   b. claude-in-chrome MCP (carregar via ToolSearch).
   c. playwright MCP (carregar via ToolSearch).
3. Salvar screenshots em `docs/screenshots/<sprint_id>/<numero>_<tela>.png`.
4. Confirmar: layout nao quebrou, texto legivel, contraste WCAG-AA, acentuacao correta no UI.

**Sprint 92a P0** estabeleceu padrao: ANTES/DEPOIS sao screenshots separados.

## Como tratar PII (CPF, CNPJ, razao social)

- **Nunca em codigo**: hard-coded e proibido. Usar `mappings/pessoas.yaml` (gitignored).
- **Nunca em commit**: hooks bloqueiam padroes regex CPF/CNPJ.
- **Nunca em log INFO**: use hash[:8] ou referencia indireta (Sprint 99 endereca).
- **Em log DEBUG**: ok, uso interno do dev.
- **Em screenshots**: redactar antes de commitar via tool de blur (manual por enquanto).
- **Em relatorios**: mascarar como `XXX.XXX.XXX-XX` ou `XX.XXX.XXX/0001-XX`.

CNPJs corporativos publicos (G4F, Americanas, Itau, etc.) nao sao PII -- podem aparecer.

## Achado colateral durante execucao

Quando voce descobre um bug ou debit fora do escopo da sprint atual:

1. **NAO** corrija dentro da sprint atual (escopo creep).
2. **NAO** deixe `# TODO` no codigo.
3. **DEVE** virar uma sprint-filha formal:
   - Crie spec em `docs/sprints/backlog/sprint_<novo_id>_*.md`.
   - Inclua hipotese + proof-of-work + acceptance criteria + estimativa.
   - Auto-dispatch o subagente `planejador-sprint` se ja estiver definido.
4. Continue executando a sprint atual.

Padrao "Zero follow-up": cada achado vira sprint-ID OU Edit-pronto, **nunca** vai para backlog informal.

## Quando declarar concluida vs quando reabrir

**Declare CONCLUIDA quando (gate anti-migue 9 checks):**
1. Hipotese declarada e validada com `grep` antes de codar (CLAUDE.md regra empirica).
2. Proof-of-work runtime real capturado em log.
3. Quando aplicavel: gate 4-way >=3 amostras (`make conformance-<tipo>`) -- bloqueante para extratores novos a partir do plan pure-swinging-mitten.
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos (foi 8/8 ate Sprint ANTI-MIGUE-04).
6. Pytest baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero "TODO depois".
8. Validador (humano OU subagent) APROVOU.
9. Spec movida para `concluidos/` com frontmatter `concluida_em: YYYY-MM-DD`.

## Criacao de extrator novo (regra explicita pos-redesign 2026-04-29)

Toda ferramenta nova exige **sprint formal**. Spec eh o contrato anti-migue.

Fluxo canonico para extrator novo (tipo X):

```
1. Spec em docs/sprints/backlog/sprint_extractor_<X>.md (problema + hipotese
   + acceptance + gate 4-way obrigatorio).
2. Implementar em src/extractors/<X>.py + registrar em src/intake/registry.py
   + adicionar em mappings/tipos_documento.yaml.
3. Fixture sintetica em tests/fixtures/.
4. Coletar >=3 amostras reais.
5. Para cada amostra: rodar pipeline, gravar marcacao no Revisor 4-way
   (etl_ok, opus_ok, grafo_ok, humano_ok).
6. `make conformance-<X>` deve retornar exit 0.
7. So entao mover spec para concluidos/ com `concluida_em: YYYY-MM-DD`.

Saltos NAO permitidos:
- Implementar sem spec.
- Declarar concluido com 1 amostra.
- Mover para concluidos/ com `make conformance-<X>` falhando.
```

**Declare CONCLUIDA quando:**
- Todos acceptance criteria atendidos com proof-of-work.
- `make lint` verde.
- `make smoke` 10/10.
- Pytest baseline mantida ou crescida.
- Spec movida para `concluidos/` com `concluida_em`.
- Commit com mensagem clara.

**Reabra a sprint quando:**
- Validador disse REPROVADO.
- Achado colateral CRITICO descoberto pos-fechamento.
- Hipotese da spec era falsa e fix nao resolve o problema real.

**NAO** declare concluida quando:
- Acceptance criteria parcial.
- Lint quebrado por outra spec (achado herdado -- conserte antes).
- Smoke aritmetico quebrou.

## Quem aprova o que

| Acao | Aprovacao necessaria |
|------|---------------------|
| Edit local em src/ | Voce mesmo (dentro do escopo da spec) |
| Adicionar teste | Voce mesmo |
| `git commit` | Voce mesmo, mensagem clara |
| `git push` | **Dono humano** |
| `gh pr create` | **Dono humano** |
| `gh pr merge` | **Dono humano** |
| Mover spec para concluidos/ | Voce mesmo (apos validacao verde) |
| Deletar arquivos em raw/ | **Dono humano** com confirmacao explicita |
| Modificar `mappings/pessoas.yaml` | **Dono humano** (PII) |
| Criar ADR | Propor draft, dono aprova nome e numero |
| Criar nova sprint em backlog | Voce mesmo (sprint-filha de achado) |
| Mover sprint para arquivadas | **Dono humano** (decisao arquitetural) |

## Regras especiais para este projeto

- Acentuacao PT-BR correta sempre. Hook bloqueia.
- Zero emojis. Hook bloqueia.
- Citacao de filosofo no final de cada arquivo `.py` novo.
- Limite de 800 linhas por arquivo (excecoes: config/, testes/, registries/).
- Logging via `rich` + `logging`, nunca `print()`.
- Paths relativos via `Path`, nunca hardcoded absolutos.

## Escala de severidade de bugs

- **P0**: bloqueia uso real do produto. Sprint imediata.
- **P1**: degrada experiencia mas nao impede. Sprint na proxima rota.
- **P2**: polish, edge case. Backlog.
- **P3**: cosmetico, futuro. Backlog longo.

Sprint nova proposta sempre declara prio.

## Quando consultar memoria persistente

`~/.claude/projects/-home-andrefarias-Desenvolvimento-protocolo-ouroboros/memory/`

Le **automaticamente** no inicio da sessao via MEMORY.md (max 200 linhas, indice).

**Atualize** quando:
- Descobre novo padrao canonico.
- Dono pede "lembre-se que X".
- Decide pelo dono em situacao recorrente (registra precedencia).

**NAO atualize** com:
- Estado efêmero (vai mudar amanha).
- Detalhes ja em CLAUDE.md ou VALIDATOR_BRIEF.
- Conversa atual (eh contexto da sessao, nao memoria).

---

*"Saber agir importa mais do que saber tudo." -- principio do operador disciplinado*
