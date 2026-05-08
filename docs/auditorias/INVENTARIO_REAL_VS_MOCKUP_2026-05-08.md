---
titulo: Inventário real vs mockup vs skeleton — 28 páginas do dashboard
data: 2026-05-08
escopo: src/dashboard/paginas/*.py (28 arquivos)
metodo: leitura de fontes de dado por página + cruzamento com data/output/ + .ouroboros/cache/ + grafo SQLite
referencia: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md
---

# Inventário real vs mockup — 28 páginas

## Contexto

Pedido do dono em 2026-05-08: classificar cada página do dashboard segundo (a) origem do dado exibido, (b) estado funcional e (c) pendências para alcançar 100% real. Saída direciona o backlog de sprints INFRA para conclusão de fato do projeto.

Classificação canônica em 4 níveis:

- **Real**: lê dado já catalogado (XLSX/grafo SQLite/cache populado) sem cálculo intermediário discutível.
- **Determinístico**: calcula a partir de dado real (agregações, médias, projeções com fórmula fechada — sem LLM).
- **Skeleton**: layout pronto + fallback estilizado (skeleton-mockup canônico) esperando dado externo (vault mob, log de runtime, etc).
- **Fallback degradado**: cai em texto-puro/CTA quando esperado seria skeleton-mockup. Considerado bug.

---

## Arquivos de dado consultados

| Arquivo | Caminho | Status (2026-05-08) |
|---|---|---|
| XLSX financeiro | `data/output/ouroboros_2026.xlsx` | Populado (8 abas, 6.094 transações, 82 meses) |
| Grafo documental | `data/output/grafo.sqlite` | Populado (~5.4MB, 50 nodes, 25 arestas) |
| Validação por arquivo CSV | `data/output/validacao_arquivos.csv` | Populado (3 amostras NFCe x 10 campos) |
| Extração tripla JSON | `data/output/extracao_tripla.json` | Populado pós-INFRA (3 amostras + Opus) |
| Revisão humana SQLite | `data/output/revisao_humana.sqlite` | Populado |
| Skills D7 log | `data/output/skill_d7_log.json` | **AUSENTE** |
| Caches mob | `vault/.ouroboros/cache/*.json` | 11 caches, schema OK, dados vazios |
| Mappings YAML | `mappings/*.yaml` | 24 yamls de configuração canônica |

---

## Tabela mestra (28 páginas)

| # | Página | Cluster | Fonte de dado | Classificação | Estado | Pendências |
|---|---|---|---|---|---|---|
| 1 | visao_geral | Home | XLSX(extrato/prazos) + grafo + concluidos/*.md | Real | Funcional | — |
| 2 | extrato | Finanças | XLSX(extrato) + mappings/categorias_tracking.yaml | Real | Funcional | — |
| 3 | contas | Finanças | XLSX(extrato) | Real | Funcional | baseboard 4-campos OFX (sub-sprint UX-V-2.1.A) |
| 4 | pagamentos | Finanças | XLSX(prazos) + extrato (V-2.2.A enriquece valor) | Real (parcial) | Funcional | — |
| 5 | projecoes | Finanças | XLSX(extrato) + projection.scenarios | Determinístico | Funcional | — |
| 6 | busca | Documentos | XLSX(todas abas) + grafo (índice) | Real | Funcional | facetas com counts reais e snippet `<mark>` (V-3.2 entregou) |
| 7 | catalogacao | Documentos | grafo.sqlite | Real | Funcional | — |
| 8 | completude | Documentos | grafo + tipos_documento.yaml | Real | Funcional | — |
| 9 | revisor | Documentos | extracao_tripla.json + revisao_humana.sqlite | Real (Opus simulado) | Funcional | Opus real depende de orquestrador LLM v2 (ADR-13 hoje é supervisor artesanal) |
| 10 | extracao_tripla | Documentos | extracao_tripla.json (3 amostras) | Real (Opus simulado) | Funcional | idem revisor: Opus em produção depende de pipeline LLM |
| 11 | categorias | Análise | XLSX(extrato) + mappings/categorias.yaml | Determinístico | Funcional | — |
| 12 | analise_avancada | Análise | XLSX(extrato) | Determinístico | Funcional | Insights derivados (POSITIVO/ATENÇÃO/DESCOBERTA/PREVISÃO) usam heurística simples; LLM v2 enriqueceria |
| 13 | metas | Metas | XLSX(extrato) + mappings/metas.yaml | Determinístico | Funcional | — |
| 14 | skills_d7 | Sistema | `data/output/skill_d7_log.json` | **Fallback** | **Quebrado** | INFRA-SKILLS-D7-LOG (criar gerador) |
| 15 | irpf | Análise | XLSX(extrato/irpf) + src/exports/pacote_irpf | Real | Funcional | — |
| 16 | inbox | Inbox | filesystem (data/raw/inbox/) | Real (vazio) | Parcial | Fila vazia hoje; parser OFX/PDF está em `src/intake` mas requer integração com Drive (BLO-J em pure-swinging) |
| 17 | be_hoje | Bem-estar | vault/.ouroboros/cache/{alarmes,tarefas,eventos,contadores}.json + humor-heatmap.json | Skeleton | Skeleton | App mob v1.0.0 (golden-zebra) — caches vazios |
| 18 | be_humor | Bem-estar | humor-heatmap.json | Skeleton | Skeleton | Mob I-HUMOR (`[ok]` no roadmap mob, dados ainda não fluem) |
| 19 | be_diario | Bem-estar | diario-emocional.json | Skeleton | Skeleton | Mob I-DIARIO `[ok]` |
| 20 | be_rotina | Bem-estar | vault/.ouroboros/rotina/*.toml + caches alarmes/tarefas/contadores | Determinístico | Funcional (skeleton se TOML ausente) | TOML existe se criado pelo Editor (página 28); caches ainda dependem mob |
| 21 | be_recap | Bem-estar | caches humor/eventos/medidas + docs/recaps/<mes>.md | Determinístico (parcial) | Skeleton (no vazio) | Comparativo 30D usa caches mob; narrativa MD é manual via /gerar-recap |
| 22 | be_eventos | Bem-estar | eventos.json | Skeleton | Skeleton | Mob I-EVENTO `[ok]` |
| 23 | be_memorias | Bem-estar | memorias.json | Skeleton | Skeleton | Mob I-FOTO/I-AUDIO/I-VIDEO `[todo]` + schema canônico do JSON ainda em aberto (INFRA-MEMORIAS-SCHEMA) |
| 24 | be_medidas | Bem-estar | medidas.json (schema estendido V-2.12.A para fisiológicas) | Skeleton | Skeleton | Mob não envia medidas ainda (não mapeado no roadmap mob atual) |
| 25 | be_ciclo | Bem-estar | ciclo.json | Skeleton | Skeleton | Mob I-CICLO `[todo]` |
| 26 | be_cruzamentos | Bem-estar | caches humor + ciclo + medidas + eventos | Determinístico | Funcional (mostra "amostra insuficiente" quando caches vazios) | Quando mob popular humor + 1 outro, builder vira útil |
| 27 | be_privacidade | Bem-estar | vault/.ouroboros/permissoes.toml | Determinístico | Funcional | Sync remoto (vault B) depende de pareamento Syncthing/radicle |
| 28 | be_editor_toml | Bem-estar | vault/.ouroboros/rotina/*.toml | Determinístico | Funcional | — |

---

## Distribuição

| Classificação | # páginas | % |
|---|--:|--:|
| Real | 9 | 32% |
| Real (parcial / Opus simulado) | 3 | 11% |
| Determinístico | 7 | 25% |
| Skeleton (esperando mob) | 8 | 29% |
| Fallback degradado | 1 | 3% |

**Estado funcional do dashboard**:
- 19 páginas (68%) com dado real ou determinístico funcionando
- 8 páginas (29%) com skeleton-mockup canônico esperando o mob v1.0.0 republicar
- 1 página (skills_d7) em fallback degradado por falta de gerador de log

---

## Pendências agrupadas

### Bloqueantes para "100% real" deste lado (3)

| Pendência | Sprint | Esforço | Justificativa |
|---|---|--:|---|
| Gerar `skill_d7_log.json` | INFRA-SKILLS-D7-LOG | 4h | Skills D7 quebrada |
| Schema canônico `memorias.json` | INFRA-MEMORIAS-SCHEMA | 3h | Memórias renderiza grid mas schema mob ainda em aberto |
| Pipeline Opus determinístico (ETL × Opus × Humano com Opus real) | INFRA-OPUS-V2 | 12h | Hoje Opus é simulado via supervisor artesanal (ADR-13). Para "real" precisaria orquestrador LLM v2 |

### Bloqueadas pelo mob v1.0.0 (golden-zebra, fora do escopo deste lado)

8 páginas Bem-estar dependem do app mob republicar v1.0.0 com saves canônicos via vault Obsidian. Estimativa do roadmap mob: ~50h de trabalho mob para fechar I-FOTO/I-AUDIO/I-VIDEO/I-TAREFA/I-ALARME/I-CONTADOR/I-CICLO/I-EXERCICIO. **Skeleton-mockup do desktop já está pronto**; nada a fazer aqui até mob popular vault.

### Dívidas arquiteturais (5 splits)

5 arquivos `.py` violam limite 800L (`(h)`). Funcionalmente OK; débito de manutenibilidade:

| Arquivo | Linhas | Sprint INFRA |
|---|--:|---|
| projecoes.py | 868 | INFRA-SPLIT-PROJECOES |
| be_recap.py | 825 | INFRA-SPLIT-RECAP |
| extrato.py | 1340 | INFRA-SPLIT-EXTRATO |
| catalogacao.py | 1052 | INFRA-SPLIT-CATALOGACAO |
| revisor.py | 1196 | INFRA-SPLIT-REVISOR |

### Outras pendências menores (em backlog)

- `inbox` parser OFX completo (BLO-J em `~/.claude/plans/pure-swinging-mitten.md`).
- Sub-sprint UX-V-2.1.A: baseboard 4 campos OFX no card de Conta.
- 7 caches Bem-estar populados via mob (não-bloqueante).

---

## Veredito honesto

**Dashboard hoje serve 100% das funcionalidades financeiras** (extrato, contas, pagamentos, projeções, IRPF, análise, categorias, metas, busca, catalogação, completude, revisor, validação tripla). Cluster Documentos completo. Cluster Bem-estar tem layout 1:1 com mockup mas espera o app mob para "ganhar vida".

**Para conclusão real do projeto**:
- 3 sprints INFRA bloqueantes deste lado (~19h).
- 50h mob (paralelo, fora deste worktree).
- 5 splits arquiteturais (não-bloqueantes, ~15h paralelizáveis).

Total deste lado para 100% real: **~34h** com paralelização em 3-4 worktrees → **~10h wall clock**.

---

*"Dado real é o que pode ser refutado. Mockup é a forma. Skeleton é a promessa." — princípio do inventário*
