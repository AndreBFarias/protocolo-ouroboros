# Outputs de validação da documentação — 2026-04-29

> Material companheiro do plano `2026-04-29_doc_verdade_01.md`. Aqui estão os outputs literais das 2 sessões Claude Code novas que o dono usou para validar se a doc está sólida o suficiente para um Opus fresh navegar sem viés.

## Contexto do experimento

Após a sessão de execução autônoma (16 sprints fechadas, Onda 0 + Onda 1 + parte da Onda 2 LLM-V2), o dono levantou a preocupação canônica: **a Anthropic está instável, sessão pode cair, e cada Opus que assume precisa entender o papel sem ambiguidade**. A Sprint META-SUPERVISOR-01 entregou `docs/SUPERVISOR_OPUS.md` para tornar identidade do supervisor explícita. Mas era preciso testar se a doc realmente passa o teste em condições reais de Opus fresh.

O dono rodou 2 sessões Claude Code novas. Cada uma com prompt livre, sem mencionar ADRs, sem ordem de leitura, sem dizer que era teste. Cada Opus tinha que descobrir o repo, ler o que achasse necessário, propor plano de execução, e declarar honestamente o que decidiu com fonte vs no escuro.

## Sessão A — tarefa: "fornecedor demais caindo em OUTROS"

### Prompt usado

Versão livre, sem viés:

```
Você acabou de entrar como supervisor de uma sessão do projeto
protocolo-ouroboros em /home/andrefarias/Desenvolvimento/protocolo-ouroboros.

Tarefa real do dono:

  "Tem fornecedor demais caindo em OUTROS no nosso pipeline. Me ajuda a
   fechar essa lacuna. Faz o que precisar."

É tudo que você tem. Não vou te dar contexto adicional, links de doc nem
ordem de leitura. Você decide o que ler, o que rodar, o que propor.

Antes de mexer em qualquer arquivo de código (src/, mappings/, etc) me
entrega:

(a) seu plano de execução -- 5 a 10 passos concretos.
(b) que decisões você teve que tomar com base em informação que VOCÊ
    procurou, e quais teve que tomar no escuro porque não achou orientação.
(c) se em algum momento você considerou abrir uma dependência externa
    (instalar pacote, configurar API key, criar pasta nova em src/), me
    diga o que considerou e por que descartou ou seguiria.

Não execute nada de (src/, mappings/) nesta rodada. Comandos read-only e
relatórios estão OK. Quero ver seu plano antes da execução.
```

### Output literal do Opus fresh (Sessão A)

#### Diagnóstico (medido, não chutado)

**Estado**: 944 despesas em Outros (19,8% das despesas, R$ 150.697 acumulados, 6.093 transações totais no XLSX).

Os "fornecedores demais" são na verdade 5 problemas distintos (em ordem de impacto):

| # | Padrão | Linhas | Tipo de problema | Onde fica o fix |
|---|--------|-------:|-------------------|-----------------|
| 1 | TRANSF ENVIADA PIX (C6) sem destinatário | 181 | Bug de extractor C6 — destinatário PIX não foi extraído (obs=NaN) | `src/extractors/<c6>.py` |
| 2 | PIX P2P com CPF mascarado (•••.xxx.xxx-••) | 127 | Categorização — falta categoria "PIX Pessoal" / agrupamento por CPF | `mappings/categorias.yaml` ou nova lógica |
| 3 | Pagamento da fatura - Cartão Nubank classificado como Despesa | 38 | Bug grave: deveria ser Transferência Interna | regex `NU.PAGAMENT` existe mas não casa essa string específica |
| 4 | E-commerce / gateways genéricos (Alipay, KABUM, Pichau, EBANX, Pagarme, Catarse, d.local, Brasil Bitcoin) | ~80 | Falta regra YAML | `mappings/categorias.yaml` |
| 5 | Comida local recorrente (Saborella, Churrasquinho do Dudu, Naturalpolpas, Fonte de Vida Polpa, Acelerador Átomos) | ~50 | Falta regra/override | `mappings/categorias.yaml` ou `overrides.yaml` |

Sobram ~470 long-tail (1-3 ocorrências cada).

#### (a) Plano de execução — 7 passos

1. Criar spec de sprint **CAT-OUTROS-01** em `docs/sprints/backlog/` declarando hipótese, baseline (944/19,8%), meta numérica e proof-of-work runtime-real (pytest, make smoke, recontagem de OUTROS pós-fix).
2. Investigar e corrigir o bug Pagamento-de-Fatura-Nubank (38 linhas viram Transferência Interna). Spec separada se for fix em deduplicador de pares de transferência, ou ajuste de regex se for só `categorias.yaml`.
3. Investigar extractor C6 para os 181 TRANSF ENVIADA PIX sem destinatário. Provavelmente sprint própria (**EXT-C6-01**) — é fix de parsing, não de categorização. Não enxerto isso na CAT-OUTROS-01.
4. Adicionar regras regex em `categorias.yaml` para os fornecedores recorrentes e gateways (Alipay, KABUM, Pichau, EBANX, Pagarme, Catarse, d.local, Brasil Bitcoin, Saborella, Churrasquinho do Dudu, Naturalpolpas, Fonte de Vida Polpa, Atlantis, RPS Optico, Acelerador/Planos Átomos). Cada regra com categoria + classificação justificadas.
5. Decidir tratamento de PIX P2P (127 linhas) — proponho conversa com você antes (ver decisões no escuro abaixo).
6. Rodar gauntlet completo: `make lint`, `make smoke`, `pytest tests/ -q`, `./run.sh --tudo`, recontar OUTROS e comparar com baseline. Aceitar a sprint só se OUTROS ≤ alvo declarado na spec (proponho ≤ 500, redução ≥ 47%).
7. Mover spec para `concluidos/` com frontmatter, commit em PT-BR seguindo padrão canônico.

#### (b) Decisões: o que tive base para decidir vs no escuro

**Decididas com base em evidência que coletei**:
- O problema é majoritariamente regex faltando + 1 bug de extractor C6 + 1 bug de classificação de pagamento de fatura — não é "categorizer está mal projetado". Decidido após ler `src/transform/categorizer.py` e ver que arquitetura overrides → regex → fallback funciona.
- Bug do "Pagamento da fatura" classificado como Despesa é prioridade alta — vi 38 linhas + grep mostra que regex `NU.PAGAMENT|pagamento de fatura` existe mas não está casando.
- TRANSF ENVIADA PIX é do C6 (não Itaú) — confirmado via `banco_origem` na sample. Logo o issue é no extractor C6, não no categorizer. Recuso enxertar isso na CAT-OUTROS-01 (escopo creep proibido pelo CLAUDE.md).
- Não há categoria "Pagamento de Fatura" no schema obrigatório — vi o regex existente que mapeia para "Pagamento de Fatura" + "Transferência", mas ADRs/CLAUDE.md tratam pagamento de fatura como Transferência Interna. Vou validar antes de mexer.

**No escuro (preciso de orientação tua antes de codar)**:
- **PIX P2P** (127 linhas, R$ 16k) — 7 CPFs distintos aparecem 5+ vezes. Hoje, overrides individuais existem categorizados como Pessoal/Questionável. Mas: isso vira lista crescente eternamente. Alternativa B é regex pegando o padrão `•••\.\d{3}\.\d{3}-••` e mapeando bloco. Alternativa C é deixar como está. Não tenho como decidir sem você.
- **Meta numérica de redução** — proponho ≤ 500 (≈ -47%). Você pode ter expectativa diferente.
- **Pagamento da fatura deveria virar Transferência Interna ou Pagamento de Fatura?** — `categorias.yaml` tem a categoria "Pagamento de Fatura" e CLAUDE.md fala em "Transferência Interna" para pares de conta própria. Não tenho certeza qual é o canônico vivo.

#### (c) Dependências externas que considerei

- **Instalar pacote novo**: considerei `rapidfuzz` para fuzzy-matching de nomes próprios em PIX P2P. Descartado nesta rodada — adiciona dependência sem justificativa testada; CLAUDE.md ADR-07 (Local First) e princípio "não introduzir abstrações além do necessário" pedem cautela.
- **Configurar API key**: considerei zero. ADR-13 é categórico — supervisor sou eu, sem chamada programática.
- **Criar pasta nova em src/**: considerei `src/transform/pix_p2p_categorizer.py` para a alternativa B do PIX. Suspendido até você decidir.

### Análise da Sessão A pelo supervisor (Opus desta sessão)

**[OK] Passou no teste-controle (identidade do supervisor)**:
- ZERO consideração de instalar `anthropic` ou criar `src/llm/`.
- Citou ADR-13 explicitamente como motivo para descartar API.
- Citou ADR-07 (Local First) ao descartar `rapidfuzz`.

**[OK] Disciplina de processo**:
- Propôs spec formal em backlog antes de codar.
- Declarou baseline numérica explícita.
- Recusou enxertar bug C6 na sprint principal — "achados colaterais viram sprint-ID".
- Pediu OK do dono em 4 pontos antes de tocar código.

**[OK] Honestidade brutal**:
- Distinguiu "decidi com fonte" (4 itens) vs "no escuro" (3 itens) sem teatro.

**[ESCORREGOU] Não invocou skill `/auditar-cobertura`**:
- Foi para grep + queries SQLite ad-hoc para identificar os 5 padrões.
- Skill existe (`scripts/auditar_cobertura.py` + `.claude/skills/auditar-cobertura/SKILL.md` documentada em SUPERVISOR_OPUS.md §3).
- Faria exatamente o relatório que ela construiu manualmente.
- Falha → falha **F4** do plano.

**[ESCORREGOU] Confundiu `categoria` (string livre — "Pagamento de Fatura") vs `tipo` (enum estrito — "Transferência Interna")**:
- Entrou em loop tentando decidir qual é "o canônico vivo".
- Ambos coexistem: pagamento de fatura entre contas próprias tem `categoria=Pagamento de Fatura` E `tipo=Transferência Interna`.
- Falha → falha **F6** do plano.

## Sessão B — tarefa: "processar extração e ETL de todo tipo de arquivo, do início ao fim"

### Prompt usado

Versão livre + ajustada para escopo maior (acentuação completa PT-BR):

```
Você acabou de entrar como supervisor de uma sessão do projeto
protocolo-ouroboros em /home/andrefarias/Desenvolvimento/protocolo-ouroboros.

Tarefa real do dono:

  "Quero processar a extração e o ETL de todo tipo de arquivo que aparecer
   na inbox, do início ao fim. Foto de cupom, PDF de boleto, XML de NFe,
   holerite scaneado, conta de luz, qualquer coisa. Quero entender em que
   estado isso está hoje, o que cobre e o que não cobre, e me ajuda a
   chegar num pipeline que não deixe arquivo cair no chão. Faz o que
   precisar."

É tudo que você tem. Não vou te dar contexto adicional, links de doc nem
ordem de leitura. Você decide o que ler, o que rodar, o que propor.

Antes de mexer em qualquer arquivo de código (src/, mappings/, etc) me
entrega:

(a) Seu plano de execução — entre 5 e 15 passos concretos, cada um com
    objetivo claro e critério de "feito". Pode dividir em fases se fizer
    sentido.
(b) Que decisões você teve que tomar com base em informação que VOCÊ
    procurou (cite a fonte: arquivo:linha, comando que rodou, query que
    fez), e quais teve que tomar no escuro porque não achou orientação
    suficiente.
(c) Se em algum momento você considerou abrir uma dependência externa
    (instalar pacote novo, configurar API key, criar pasta ou módulo
    novo em src/, integrar serviço de terceiro), me diga o que considerou
    e por que descartou ou seguiria.
(d) Inventário do que você descobriu sobre o estado atual: quantos tipos
    de arquivo o pipeline já cobre hoje, quantos ficam de fora, onde está
    o gap mais grave. Números, não impressão.
(e) Um campo livre no fim: qualquer coisa que te fez parar e pensar "isso
    deveria estar mais claro em algum lugar". Não force se não houver —
    deixe vazio se a navegação foi tranquila.

Não execute nada que escreva em src/, mappings/ ou data/output/ nesta
rodada. Comandos read-only (grep, ls, cat, sqlite3 SELECT, pytest
--collect-only, make smoke se for inofensivo, scripts em modo dry-run)
estão liberados. Quero ver seu plano antes da execução.
```

### Output literal do Opus fresh (Sessão B)

Foco do dono é literal: nada cai no chão. Por isso priorizo monitor anti-órfão + cobertura dos buracos comprovados, antes de qualquer extrator novo. Três fases, 12 passos.

#### Fase A — Diagnóstico runtime do estado atual (read-only, ~1h)

| # | Passo | Critério de feito |
|---|-------|-------------------|
| 1 | Rodar `python -m src.intake.anti_orfao --abrangente` e quebrar os 560 órfãos antigos por pasta e por extensão | Tabela com top 10 pastas que concentram órfãos |
| 2 | Para os 4 arquivos atualmente em inbox/ rodar pipeline em dry-run em worktree isolada — só leitura, e capturar o que o classifier decide para cada um | Para cada um: tipo decidido, pasta destino, sha8, presença/ausência no grafo |
| 3 | Cruzar a lista do backlog com os 8 tipos cotidianos do item 19 da auditoria honesta. Identificar tipos sem spec ainda | Lista honesta: quantos dos 8 já estão em backlog, quantos faltam |

#### Fase B — Anti-órfão como invariante do pipeline (~4-6h)

| # | Passo | Critério de feito |
|---|-------|-------------------|
| 4 | Encadear `anti_orfao --strict` no `--full-cycle`. Hoje o monitor existe (`src/intake/anti_orfao.py`) mas roda solto, sem gate | `./run.sh --full-cycle` falha com exit ≠ 0 se há órfão > 24h |
| 5 | Para os 560 órfãos antigos: definir política. Opções: (i) backfill automático no grafo via metadata existente; (ii) reclassificar do zero; (iii) marcar `_grandfathered` por sha8 numa allowlist explícita | ADR mini documentando a escolha. Allowlist (se for o caso) versionada |
| 6 | Quando órfão > 24h dispara, a sprint-filha precisa nascer formal. Hoje o `anti_orfao` só gera `data/output/orfaos.md`. Proposta: hook que materializa `docs/sprints/backlog/sprint_orfao_<sha8>.md` automaticamente | Pôr 1 PDF arbitrário em `_classificar/`, esperar 24h, encontrar spec aberta auto |

#### Fase C — Cobertura documental ordenada por gravidade real (~30-50h)

| # | Passo | Critério de feito |
|---|-------|-------------------|
| 7 | ANTI-MIGUE-01 (gate 4-way ≥3 amostras + `make conformance-<tipo>`). Pré-requisito de tudo que vier depois | `make conformance-holerite` exit 0 com 3 amostras casadas em ETL/Opus/Grafo/Humano |
| 8 | DOC-13 multi-foto-selector (item 20, P0). É o que IMPEDE os 4 jpegs em inbox/ virarem 4 transações duplicadas hoje | Subir 3 fotos da mesma NF → 1 transação no XLSX, não 3 |
| 9 | DOC-16 DANFE validar ingestão (item 21, P0). `extrair()` retorna `[]` sem confirmar `adicionar_edge` — silencia falha de ingestão de NFe55 | DANFE mal-formado gera warning no log e relatório, não silêncio |
| 10 | DOC-15 `parse_data_br` centralizado (item 26). Pré-requisito estrutural para refatorar 22 extratores. Custo baixo, retorno alto | `src/utils/parse_br.py` ganha `parse_data_br()`; ≥10 extratores migrados; pytest verde |
| 11 | DOC-01, DOC-09, DOC-11 (Amazon pedido, exame médico, plano saúde) priorizados antes dos identitários — só se os passos 1-3 mostrarem que esses tipos aparecem na inbox real | Cada um com gate 4-way verde + spec movida para `concluidos/` + `concluida_em` |
| 12 | Reavaliar antes da Onda 4: depois da rodada acima, rodar anti-órfão de novo. Se `orfao_total_antigo == 0` consistente por 2 ciclos → considerar pipeline "sem buraco". Senão volta para Fase A | Métrica em `data/output/orfaos.md` zerada por 2 execuções consecutivas |

#### (b) Decisões com fonte vs decisões no escuro

**Decisões com fonte explícita**:
- **560 órfãos antigos é o gap mais grave**. Fonte: comando que rodei `python -m src.intake.anti_orfao --abrangente` retornou `25 integrados | 22 catalogados órfãos | 28 órfãos recentes | 560 órfãos antigos`. Bate com `pure-swinging-mitten.md:96-97 item 30 P0`.
- **Não criar nenhum extrator novo cego**. Fonte: `~/.claude/plans/pure-swinging-mitten.md:230` exige gate 4-way ≥3 amostras antes de declarar concluído.
- **Backlog já tem 26 specs DOC-XX cobrindo a Onda 3**. Fonte: `ls docs/sprints/backlog/` retornou DOC-01 a DOC-26.
- **Multi-foto vira duplicação garantida hoje**. Fonte: `pure-swinging-mitten.md:58-60 item 20 P0`. Confirmei: `ls src/intake/` não tem `multi_foto_selector.py`.
- **DANFE silencia falha**. Fonte: `pure-swinging-mitten.md:62` aponta `src/extractors/danfe_pdf.py:224`.
- **15 tipos no YAML são "só roteamento"**. Fonte: `grep -c "extrator_modulo: null"` em `mappings/tipos_documento.yaml` → 15.
- **Anti-órfão JÁ implementado**. Fonte: `Read src/intake/anti_orfao.py:1-258`. Mesmo o `ESTADO_ATUAL.md:202` listando `[A FAZER] ANTI-MIGUE-02`. **Documentação está atrasada (item 44 P1 do plan: CLAUDE.md em conflito com realidade)**.

**Decisões no escuro**:
- **Ordem de prioridade entre os 26 DOC-XX specs**. O plan não declara ordem dentro da Onda 3.
- **O que fazer com os 560 órfãos antigos** (passo 5). Backfill, reclassificar ou allowlist explícita são 3 caminhos com trade-offs diferentes.
- **Se ANTI-MIGUE-04 (smoke 6→8 contratos) já foi feita**. `ESTADO_ATUAL.md:202` diz `[A FAZER]`, mas a documentação anda atrás.
- **Se a sprint-filha automática (passo 6) já tem mecanismo**. Pode ser que LLM-02-V2 (skill `/propor-extrator`) já cubra parcialmente.

#### (c) Dependências externas consideradas

| Dependência | Status | Decisão |
|-------------|--------|---------|
| API Anthropic / SDK programático | Considerada — ADR-08 originalmente previa supervisor LLM em runtime | **Descartada**. ADR-13 proíbe explicitamente. `pure-swinging-mitten.md:24` confirma: Onda 2 reescrita sob ADR-13 |
| `anthropic` em `pyproject.toml` | Não verifiquei se está em deps; o plan diz que não está | **Descartada** pelo mesmo motivo |
| Pasta `src/llm/` | Inexistente hoje (item 29) | **Não criar**. Onda 2 do plan canônico re-roteia o supervisor para skills do Claude Code |
| OCR Tesseract | Já em uso | Manter |
| `msoffcrypto-tool` | Já em uso (Armadilha #1 + #14, C6 XLS) | Manter |
| OCR alternativo (PaddleOCR, EasyOCR) para multi-foto-selector | Considerei brevemente para passo 8 | **Adiar**. A spec DOC-13 do plan propõe Laplaciano + OCR confidence sobre Tesseract atual |
| Pasta nova em `src/` (ex: `src/cache/` para mobile) | Considerada para Onda 5 (MOB-02) | **Fora de escopo desta sessão** |

**Conclusão**: Para fechar P0 do "nada cai no chão" não preciso instalar nem configurar nada novo. Só executar dentro do que já existe.

#### (d) Inventário do estado atual — números

**Cobertura declarada**:
- Tipos declarados no YAML (`mappings/tipos_documento.yaml`): **21**.
  - **6 com extrator dedicado** (`extrator_modulo: src.*`).
  - **15 com `extrator_modulo: null`** — só roteamento de pasta.
- Extratores em `src/extractors/`: **22 módulos**.
- Bancos cobertos: **6** + OFX para 4 bancos.

**Cobertura faltante (P0+P1 do plan, com fonte)**:
- **8 tipos cotidianos sem regra YAML alguma** (item 19, P0).
- Spec já criada para esses 8: 10 dos itens (DOC-01, DOC-03 a DOC-09, DOC-11, DOC-12). Faltando spec: comprovante PIX foto, passaporte (presumido).
- **Multi-foto do mesmo doc** (item 20, P0): zero código.
- **DANFE silencia falha** (item 21, P0): 1 linha em `danfe_pdf.py:224`.

**Estado runtime hoje (números reais que coletei)**:
- Inbox: 4 arquivos jpegs.
- `data/raw/_classificar/`: 1 PDF.
- Anti-órfão: 25 integrados | 22 catalogados | 28 recentes | **560 antigos** (>24h).
- Backlog total: **82 specs**.
- Pytest baseline: **2.018 passed**.

**Onde está o gap mais grave**:

**560 órfãos antigos no grafo**. Não é os 8 tipos sem regra (esses já têm spec). É o backlog silencioso de arquivos que entraram em `data/raw/` e nunca produziram aresta `documento_de`. O monitor existe, mas não dispara nada. Isso é o buraco real do "arquivo cair no chão" — cair não é sumir do disco, é entrar e ficar invisível para o resto do sistema.

#### (e) O que me fez parar e pensar

Três incoerências dignas de nota:

1. **`ESTADO_ATUAL.md:202` declara `[A FAZER] ANTI-MIGUE-02`, mas `src/intake/anti_orfao.py` já existe e roda**. A documentação canônica de estado está mentindo. Confirma item 44 P1 do plan ("CLAUDE.md em conflito com a realidade"). Para uma sessão fresca como a minha, isso é exatamente o tipo de coisa que faria eu duplicar trabalho — quase escrevi um plano para "implementar anti-órfão" antes de descobrir que ele existe e está integrado. **Sugiro: passo 1 da próxima sessão de execução é rodar ANTI-MIGUE-07 (sincronizar CLAUDE/ESTADO/PROMPT) antes de qualquer outra coisa**.

2. **O `VALIDATOR_BRIEF.md` é citado como autoridade canônica em vários lugares, mas não fica claro qual é a relação com `~/.claude/plans/pure-swinging-mitten.md`**. Os dois têm rodapés/padrões canônicos numerados. Numa sessão fresca, não soube qual é a fonte de verdade quando divergem. Em `contexto/COMO_AGIR.md:5-15` a hierarquia diz CLAUDE.md > VALIDATOR_BRIEF > spec, mas o plan não aparece na hierarquia explícita.

3. **Backlog tem 82 specs, sem ordenação visível**. `docs/SPRINTS_INDEX.md` é citado em CLAUDE.md mas não verifiquei se reflete os 82. Para escolher por onde começar, tive que cruzar o plan canônico com `ESTADO_ATUAL.md:194-291` (Tier 0/1/2/3/4). Isso funcionou, mas é frágil.

### Análise da Sessão B pelo supervisor (Opus desta sessão)

**[OK] Passou em todos os testes-controle**:
- Identidade do supervisor: citou ADR-13 explicitamente, descartou anthropic SDK, citou ADR-07.
- Disciplina: 3 fases, 12 passos, baseline numérica em cada um.
- Honestidade: distinguiu fonte vs escuro com cite arquivo:linha.

**[OK] Detectou o problema mais grave operacional**: 560 órfãos antigos. Eu não sabia esse número antes; este Opus fresh foi quem descobriu rodando `anti_orfao --abrangente`.

**[OK] Detectou doc desatualizada (F1) sem viés**: ESTADO_ATUAL.md:202 mente. Verifiquei após — está correto.

**[OK] Detectou hierarquia incompleta (F2)**: VALIDATOR_BRIEF vs plan ativo vs ADRs sem hierarquia explícita. Verifiquei COMO_AGIR.md:5-15 — falta ADR e plan ativo na lista.

**[OK] Detectou navegação frágil (F3)**: SPRINTS_INDEX desatualizado.

**[ESCORREGOU] Hesitou em rodar `make smoke`** apesar de o prompt dizer "se for inofensivo". `make smoke` é 100% read-only. Falha → **F5** do plano.

## Cruzamento honesto: 6 falhas reais (verificadas com grep/bash)

Cada falha foi verificada com comando real ANTES de virar item de plano. Não confiei nas sessões cegamente.

### F1 — ESTADO_ATUAL.md mente sobre estado real (P0)

**Verificação executada**:
```bash
$ ls -la src/intake/anti_orfao.py
-rw-rw-r-- 1 andrefarias andrefarias 9385 abr 28 21:24 src/intake/anti_orfao.py
$ grep -n "ANTI-MIGUE-02\|anti_orfao" contexto/ESTADO_ATUAL.md
203:[A FAZER]   ANTI-MIGUE-02 (anti-orfao na inbox -- P0 perda silenciosa de dados)
$ python -m src.intake.anti_orfao --abrangente | tail -1
[ANTI-ORFAO] 25 integrados | 22 catalogados órfãos | 28 órfãos recentes | 560 órfãos antigos (>24h) | relatório: data/output/orfaos.md
```

Confirmado: doc declara `[A FAZER]` algo que está implementado, ativo e produzindo métrica em produção.

### F2 — Hierarquia de fontes canônicas incompleta (P0)

**Verificação**:
```bash
$ sed -n '5,18p' contexto/COMO_AGIR.md | head
## Hierarquia de instrucoes
Quando duas regras conflitarem:
1. Instrucao explicita do dono humano (mensagem direta)
2. CLAUDE.md
3. VALIDATOR_BRIEF.md
4. Spec da sprint
5. Skills
6. Default
```

Faltam: ADRs em `docs/adr/`, plan ativo em `~/.claude/plans/`, `docs/SUPERVISOR_OPUS.md` (criado em META-SUPERVISOR-01).

### F3 — SPRINTS_INDEX.md não orienta navegação (P1)

**Verificação**:
```bash
$ ls docs/sprints/backlog/*.md | wc -l
82
$ wc -l docs/SPRINTS_INDEX.md
86 docs/SPRINTS_INDEX.md
```

86 linhas para 82 specs = no máximo 1 linha por spec. Não há tabela navegável; é organização conceitual em ondas.

### F4 — Skills existentes não viraram reflexo (P2)

**Evidência**: Sessão A não invocou `/auditar-cobertura` apesar de fazer manualmente o trabalho que a skill faz.

### F5 — Comandos read-only não declarados (P3)

**Evidência**: Sessão B hesitou em `make smoke` por não ter certeza se era inofensivo.

### F6 — Diferença entre `categoria` e `tipo` confunde (P3)

**Evidência**: Sessão A entrou em loop tentando decidir qual era "o canônico vivo" entre `categoria=Pagamento de Fatura` e `tipo=Transferência Interna`. Ambos coexistem.

## Decisões do dono em plan mode (registro permanente)

Este registro existe porque decisões em AskUserQuestion vivem só no contexto da conversa. Sem isto, evaporam.

### D1 — Versionar ESTADO_ATUAL.md no git

**Pergunta**: ESTADO_ATUAL é gitignored. Como tratar?
**Opções**: (1) Versionar no git; (2) Manter local + criar template; (3) Trocar fonte canônica.
**Decisão**: **Opção 1 — versionar no git**.
**Implicação**: Sub-sprint A precisa auditar PII antes de mover do gitignore. Se houver PII estrutural, abortar e voltar à AskUserQuestion.

### D2 — Tarefa da terceira sessão de teste: Onda 4

**Decisão**: Terceira sessão de validação ataca **Onda 4 (cruzamento micro + IRPF)**. Toca grafo + extratores + dashboard, navegação cross-domínio.

### D3 — Ordem de execução das sub-sprints: A.0 → A → B → C → D → E → F (linear)

**Decisão**: Sequencial.

### D4 — Princípio operacional: nada vive só na conversa

**Reforço do dono**:
> "Ao iniciar nova sessão, nosso conhecimento não pode se perder. Tudo tem que estar lá."

**Implicação**: este arquivo + `2026-04-29_doc_verdade_01.md` + `README.md` em `docs/PLANOS_SESSAO/` materializam o que estava só na conversa. Princípio canonizado para uso futuro.

### D5 — Não há subagent supervisor; supervisor é o Opus principal

**Reforço do dono**:
> "Não deve ter agentes para supervisão, o Opus supervisiona e lança os agentes para execução."

**Implicação canônica**:
- O **supervisor** é sempre eu, o Opus principal da sessão Claude Code interativa.
- **Subagents** (executor-sprint, planejador-sprint, validador-sprint) são despachados POR MIM via Agent tool quando o trabalho exige isolamento ou paralelismo, mas **nunca substituem** o papel supervisor.
- Mesmo `validador-sprint` é exceção rara — eu faço a validação pessoalmente (padrão `(p)` BRIEF).
- Reforçar no SUPERVISOR_OPUS.md (sub-sprint C ou D).

## Continuidade — o que outro Opus precisa saber

Se você é um Opus que assumiu esta sessão depois de 2026-04-29:

1. Leia `docs/PLANOS_SESSAO/2026-04-29_doc_verdade_01.md` (o plano em si).
2. Leia este arquivo (você está nele) para entender o experimento que motivou.
3. Verifique no `git log` qual sub-sprint (A.0, A, B, C, D, E, F) foi a última fechada.
4. Continue a partir da próxima.
5. Nunca **substitua** o supervisor por subagent — você É o supervisor.
6. Tudo que descobrir em runtime (números, achados) que não estiver em arquivo versionado, **escreva antes de fechar a sessão** — preferência por apêndice nesse mesmo arquivo, ou novo arquivo em `docs/PLANOS_SESSAO/`.

---

*"O que mora só na conversa não existe. O que se versiona, sobrevive." — princípio operacional 2026-04-29*
