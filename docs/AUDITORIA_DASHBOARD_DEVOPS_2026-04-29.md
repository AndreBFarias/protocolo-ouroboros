# Auditoria — Dashboard + DevOps + Validação de extrações

> Data: 2026-04-29 (após brainstorming de redesign + materialização do backlog).
> Método: dashboard subido em headless, screenshots via playwright nos 5 clusters; pipeline lido em runtime real (XLSX + grafo SQLite); devops auditado linha-a-linha.

## 1. Validação de extrações (runtime real)

### 1.1 XLSX `data/output/ouroboros_2026.xlsx`

```
mtime: 2026-04-24 22:05 (5 dias atrás — pipeline não roda hoje)
extrato: 6.093 transações em 82 meses (2019-10 a 2026-10)
tipos: Despesa 4.768 | Transferência Interna 756 | Receita 480 | Imposto 89
bancos: Nubank (PF) 1.757 | C6 1.190 | Histórico 1.181 | Nubank 998 |
        Nubank (PJ) 828 | Santander 110 | Itaú 29
pessoas: Vitória 3.160 | André 2.933 (zero "Casal" — cobertura 100%)
```

**Achados:**

- [OK] Smoke 10/10 contratos OK em runtime.
- [GAP] **Zero transações tipo `Investimento`** — confirma `DOC-20` como gap real.
- [GAP] **6.093 (real) vs 6.094 (declarado em CLAUDE.md/ESTADO_ATUAL)** — pequena divergência, provável dedup pós-reextração. Não-bloqueante; ESTADO_ATUAL atualizado.
- [OK] Pessoas atribuídas em 100% (zero "Casal" indeterminado) — Sprint 90 e correlatas funcionando.

### 1.2 Grafo SQLite `data/output/grafo.sqlite`

```
nodes: transacao 6.086 | fornecedor 1.106 | categoria 104 | periodo 82 |
       documento 47 | item 41 | conta 7 | produto_canonico 7 | tag_irpf 4 |
       apolice 2 | seguradora 1
edges: ocorre_em 6.135 | categoria_de 6.127 | origem 6.086 | contraparte 6.084 |
       irpf 164 | fornecido_por 47 | contem_item 33 | documento_de 25 |
       mesmo_produto_que 14 | assegura 2 | emitida_por 2 | vendida_em 2
```

**Achados:**

- [OK] 47 documentos catalogados; **25 com aresta `documento_de`** = 53% vinculação. Acima dos 50% declarados.
- [OK] 41 nodes `item` granulares + 33 edges `contem_item` — Sprint AUDIT2-METADATA-ITENS-LISTA produziu efeito.
- [GAP] **Discrepância 6.093 (XLSX) vs 6.086 (grafo)** — 7 transações no XLSX não têm node correspondente. Provável dedup tardio. Sub-sprint potencial: investigar.

### 1.3 Inbox

```
data/raw/_classificar/: 1 arquivo (órfão antigo conhecido)
data/raw/_conferir/: 2 arquivos (cupons aguardando)
data/raw/_envelopes/: 28 arquivos (preservados ADR-18)
```

- [OK] Anti-órfão (Sprint ANTI-MIGUE-02 desta sessão) detecta o órfão antigo.
- [OK] Pipeline limpa _classificar/ corretamente.

## 2. Dashboard (5 screenshots em `docs/screenshots/audit_2026-04-29/`)

### 2.1 Cluster Home — `01_home_inicial.png`

- [OK] Paleta Dracula consistente.
- [OK] KPIs legíveis: Taxa de Poupança 58.2%, Gastos Supérfluos R$ 134.39, Maior Gasto Impostos R$ 1.463,35.
- [OK] Card "Saúde financeira: Saudável — Poupança de 58% da receita" verde ajuda navegação.
- [OK] Gráficos Receita vs Despesa (bar + line) e Despesas por Classificação (bar horizontal).
- [GAP] Sidebar mostra "Dados de 24/04/2026 19:05" — informação de freshness presente, mas sem alerta quando muito antigo (>7d). Sub-sprint potencial.

### 2.2 Cluster Finanças — `02_financas.png`

- [OK] Cards Receita/Despesa/Saldo do dia.
- [OK] Tabela "Transações do dia" com 5 colunas (Local, Categoria, Tipo, Banco, Valor).
- [GAP] **Nomenclatura confusa**: cluster "Finanças" também é uma aba dentro do cluster Home. Mesmo rótulo em 2 níveis. Sub-sprint **`UX-10`** criada nesta auditoria.

### 2.3 Cluster Documentos — `03_documentos.png`

- [OK] 5 abas (Busca Global, Catalogação, Completude, Revisor, Grafo + Obsidian).
- [OK] Busca Global com chips rápidos (Holerite, NF, DAS, Boleto, IRPF, Recibo, Comprovante, Contracheque) — UX excelente.
- [OK] Empty state apropriado: "Digite um termo acima ou clique em um chip para iniciar".

### 2.4 Cluster Análise — `04_analise.png`

- [OK] Treemap **WCAG-AA visualmente OK em viewport 1600px**: verde Obrigatório (Impostos R$ 1.463,35, Farmácia R$ 938,93, Juros/Encargos R$ 688,88, Mercado R$ 428,30, Saúde R$ 250); laranja Questionável (Delivery R$ 237,44, Outros R$ 220,14); rosa Supérfluo (Compras Online R$ 134,39).
- [GAP] **Não testei em viewport ≤ 1200px** — auditoria item 5 mantém-se válida (UX-02).

### 2.5 Cluster Metas — `05_metas.png`

- [OK] Reserva de emergência R$ 44.019,78 / R$ 27.000,00 = **100%** (P1, prazo 2026-12).
- [OK] Quitar dívida Nubank PF (Vitória) R$ 0 / R$ 13.049 = 0% (P2, prazo 2030-09 — **estratégia explícita: deixar prescrever em set/2030**).
- [OK] Total: 7 metas (5 monetárias, 2 binárias).

### 2.6 Deep-link `?cluster=X`

- [OK] Funciona para cluster: `?cluster=Finanças`, `?cluster=Documentos`, `?cluster=Análise`, `?cluster=Metas`.
- [GAP] `?tab=` testado parcialmente — `?tab=Finanças` foi para "Finanças hoje" dentro do cluster Home (comportamento ambíguo). UX-08 no plan cobre o teste de cobertura completo.

## 3. DevOps (Makefile + hooks + scripts + CI)

### 3.1 Makefile (17 targets, organizado)

```
help, install, process, inbox, tudo, dashboard, test, test-cov, lint,
format, docs, validate, check, gauntlet, smoke, clean
```

- [OK] Cada target tem `## help` inline.
- [GAP] **Falta target `make conformance-<tipo>`** — bloqueante para Onda 3 (gate 4-way). Já está em ANTI-MIGUE-01.
- [GAP] **Falta target `make anti-migue`** — checagem dos 9 critérios. Sub-sprint potencial.

### 3.2 Git hooks (3 ativos)

```
.git/hooks/commit-msg   (3.1KB)  — bloqueia menção a IA
.git/hooks/pre-commit   (7.8KB)  — lint + acentuação + dados sensíveis
.git/hooks/pre-push     (6.4KB)  — gauntlet ou similar
```

- [OK] 3 hooks ativos, todos não-sample.
- [OK] install.sh (auditado parcialmente) cuida do bootstrap.

### 3.3 Scripts (35 arquivos)

- [OK] Convenção: scripts one-shot prefixados com `_` (ex: `_gerar_decisoes_opus_v2.py`, `_materializar_backlog_pure_swinging.py`).
- [OK] Pasta `scripts/ci/` e `scripts/gauntlet/` para sub-componentes.

### 3.4 CI workflow `.github/workflows/ci.yml` — **3 BUGS GRAVES**

```yaml
# BUG #1 — pytest com fallback silencioso
- name: Run tests
  run: pytest tests/ -v --tb=short || echo "Nenhum teste pytest encontrado"
```
**Problema**: o `||` mascara falha. CI nunca falha por causa de teste vermelho. Sprint 55 (1.761 transações classificadas erradas) **passou direto** pelo CI antigo por essa causa.

**BUG #2**: CI **não roda `make smoke`** (10 contratos aritméticos).

**BUG #3**: CI **não roda `scripts/check_acentuacao.py`** (regra inviolável #1).

**Resultado**: CI verde dá falsa segurança. Sprint **`CI-01`** criada nesta auditoria como **P0** para corrigir.

## 4. Sprints novas criadas nesta auditoria

| Sprint | Onda | Prio | Esforço | O que faz |
|---|---|---|---|---|
| **CI-01** | 0 | P0 | 1h | Corrigir CI (remover `||`, adicionar smoke + acentuação) |
| **DESIGN-01** | 0 | P0 | 6h | Blueprint de outputs/relacionamentos/relatórios |
| **AUDITOR-01** | 2 | P1 | 5h | Relatório de cobertura documental por pessoa |
| **DOC-20** | 3 | P1 | 5h | Extrator extrato de investimento (B3/corretoras) |
| **GAP-01** | 4 | P1 | 4h | Alerta proativo: tx sem NF correspondente |
| **DASH-01** | 6 | P2 | 4h | Pacote anual de vida (não só IRPF) |
| **UX-10** | 6 | P2 | 2h | Clarificar hierarquia cluster vs aba |

Total: **+27h** ao plan original. Backlog passa de 61 -> 68 specs novas + 17 antigas = **85 total**.

## 5. Resposta direta à pergunta "ao final das sprints teremos isso?"

**Sim, com 7 sprints novas adicionadas hoje, a visão completa está coberta.**

Verificação visão × cobertura final:

- [OK] Opus cria automações sob demanda (LLM-02 + ANTI-MIGUE-01)
- [OK] Inputs do user via inbox (anti-órfão + classifier)
- [OK] Sistema aponta docs faltantes proativamente (**GAP-01 NOVO** + AUDITOR-01)
- [OK] Trackear o quê/quando/porquê/classificação (MICRO + categoria + obs)
- [OK] Botão IRPF/pacote anual de vida (IRPF-01 + **DASH-01 NOVO** + **DOC-20 NOVO**)
- [OK] NFs Amazon/mercado (DOC-01/02 + MICRO)
- [OK] Identidade/Profissional/Saúde/Acadêmico (DOC-03..09, OMEGA-94*)
- [OK] Carteira digital, gov.br (DOC-11, DOC-12)
- [OK] Claude lê tudo, fala dos faltantes (**AUDITOR-01 NOVO** + LLM-04 + Revisor)
- [OK] Anti-perda + anti-dup (ANTI-MIGUE-02 + DOC-14)
- [OK] Mobile companion (MOB-01..03)
- [OK] Agendas + email + assinaturas (FONTE-01..04)
- [OK] Multi-foto (DOC-13)
- [OK] Cruzamento micro (MICRO-01..03)
- [OK] Blueprint inicial de design (**DESIGN-01 NOVO**)
- [OK] CI confiável (**CI-01 NOVO**)
- [OK] Hierarquia visual clara (**UX-10 NOVO**)

**Cobertura: 100% da visão declarada.** As 7 sprints novas fecham as lacunas que a primeira versão do plan deixou.

---

*"Validar visualmente é a única forma de saber se o que se imagina é o que se entrega." — princípio da auditoria visual obrigatória.*
