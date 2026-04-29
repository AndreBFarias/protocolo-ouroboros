# Ouroboros — Auditoria Honesta + Plano de Fechamento

> **Atualização canônica 2026-04-29 (Sprint DOC-VERDADE-01.B):** este plano é **aspiração de fechamento**, NÃO verdade do estado atual. Para o estado real consulte `git log --oneline` + `ls docs/sprints/concluidos/` + `python scripts/auditar_estado.py`. Hierarquia de fontes em `contexto/COMO_AGIR.md §Hierarquia de instrucoes`. Sub-sprints já fechadas desta auditoria estão registradas em `docs/HISTORICO_SESSOES.md` e em `docs/sprints/concluidos/`. Cópia versionada deste plano (mais o histórico de mudanças nele) em `docs/PLANOS_SESSAO/`.

> **Status:** PLANO em revisão — gerado em 2026-04-29.
> **Pedido do dono:** "overview sem viés, honesto, procurando todas as falhas de layout, extração, falta de integração, bugs não observados, documentação e afins". Sem suavizar.
> **Slug:** pure-swinging-mitten

---

# PARTE I — AUDITORIA HONESTA (o que falta pro projeto estar finalizado)

Cada achado foi verificado por agente Explore com leitura direta do código. Severidades **P0** (bloqueia uso real), **P1** (degrada experiência), **P2** (funcionalidade incompleta), **P3** (cosmético/observabilidade). Onde os 3 reports divergiram, aparece o número correto.

## §1 — Layout, UX e dashboard

### P0 — Componentes fora do design system Dracula (Sprint 92c não aplicada onde deveria)
1. `src/dashboard/componentes/preview_documento.py:72,80,100` — `st.error/warning/info` no modal de transação (PDF inexistente, > 5 MB).
2. `src/dashboard/app.py:207,333,445` — `st.warning/error` no carregamento principal (XLSX ausente, cluster desconhecido).
3. `src/dashboard/componentes/modal_transacao.py:95,101` — `st.info/warning` quando documento sem caminho/comprovante.
4. `src/dashboard/paginas/busca.py:726` — `st.success` em ação de cópia para `exports/`.

### P1 — Acessibilidade WCAG-AA frágil
5. `src/dashboard/paginas/categorias.py:38-66` — Treemap testado em 1600×1000 mas não em 1200×700 nem mobile; verde (#50FA7B) e amarelo (#F1FA8C) com contraste ~3.2:1 (limite WCAG-AA).
6. `src/dashboard/paginas/analise_avancada.py:204-220` — Heatmap em fundo Dracula (#282A36) faz células de valor baixo desaparecerem.

### P2 — Drill-down incompleto (Sprint 87 listou como pendência, não foi entregue)
7. `analise_avancada.py:157-174` — Sankey sem clique→filtro.
8. `analise_avancada.py:210-220` — Heatmap não conecta ao Extrato.
9. `pagamentos.py:230+` — Bar de Pagamentos sem drill-down por cartão/mês.
10. `projecoes.py` — Line plot sem interatividade.
11. `completude.py:97+` — Bar de completude sem drill-down.

### P2 — Revisor 4-way com layout rígido
12. `src/dashboard/paginas/revisor.py:682` — `st.columns(4)` sem responsividade nem `use_container_width`. Em 900px, colunas colapsam abaixo de 100px cada.
13. `revisor.py:71` — `ITENS_POR_PAGINA = 10`, mas dimensões de 1 item com 50+ subitens são renderizadas inline sem scroll/expand.

### P2 — Acentuação e `# noqa: accent` órfão
14. **45 ocorrências** de `# noqa: accent` (não 8, não 6) em `src/dashboard/`, `src/extractors/`, `src/graph/`. Sprint 95c trata como aceito via `pyproject.toml:72 external = ["accent"]`, mas 6 docstrings têm acentuação quebrada (`dados.py:395,399`, `busca_indice.py:8`, `extrato.py:149`, `grafo_pyvis.py:166`, `categorias.py:156`).

### P3 — Pyvis sem fallback decente
15. `src/dashboard/componentes/grafo_pyvis.py:24,212` — Quando bzip2 ausente, retorna `<p>pyvis não instalado…</p>` sem spinner/timeout/aviso.

### P3 — Coluna "Doc?" no Extrato sem observabilidade
16. `src/dashboard/paginas/extrato.py:144-168` — `_carregar_ids_com_doc()` é `@cache_data(ttl=30)`; falha do grafo cai em fallback silencioso (set vazio) sem registrar erro/contagem.

### P3 — Snapshot histórico sem timestamp na UI
17. `src/dashboard/paginas/contas.py:26-30` — Aviso "snapshot 2023" hardcoded, sem data dinâmica. Inventário/Prazos/Dívidas Ativas não têm aviso na UI (XLSX tem cabeçalho mas dashboard pula).

### P3 — Deep-link `?tab=` não testado em todas as 13 abas
18. `src/dashboard/app.py:58-91` — Sprint 100 deu por encerrada, mas `tests/test_dashboard_deeplink_tab.py` não existe ou não cobre as 13 abas + transição entre clusters.

---

## §2 — Extração e qualidade de dados

### P0 — Documentos cotidianos sem regra YAML nem extrator
19. **8 tipos sem regra alguma em `mappings/tipos_documento.yaml`**: pedido Amazon (HTML/PDF), comprovante PIX em foto (não app banco), exame médico, carteirinha de plano, RG/CNH/passaporte digital, diploma, histórico escolar, certidão de nascimento. Sequer detectáveis pelo classifier — caem silenciosamente em `_classificar/` e o usuário não percebe.

### P0 — Multi-foto do mesmo documento causa duplicação garantida
20. **Zero código** em `src/intake/` para escolher melhor entre N fotos do mesmo doc. Cenário: usuário tira 3 fotos da mesma NF, OCR extrai 3x e o pipeline cria 3 transações idênticas (escapando do dedup transacional porque o hash difere).

### P0 — DANFE retorna `[]` sem validar ingestão no grafo
21. `src/extractors/danfe_pdf.py:224` — `extrair()` retorna `[]` final sem confirmar se o `db.adicionar_edge(...)` no grafo foi bem-sucedido. Se o SQL falha, o ETL declara "0 transações" sem warning.

### P1 — 15 tipos com `extrator: null` em `mappings/tipos_documento.yaml`
22. cupom_garantia_estendida (L46), das_parcsn (L116), das_mei (L132), irpf_parcela (L148), comprovante_cpf (L163), certidao_receita_cnpj (L179), extrato_c6_pdf (L194), receita_medica (L242), garantia_fabricante (L258), conta_agua (L327), contrato (L359), cupom_fiscal_foto (L406), recibo_nao_fiscal (L422), fatura_cartao (L275 — doc menciona extrator que não encontrei). São **só roteamento de pasta**, sem extração de dados estruturados.

### P1 — OCR de energia com regex frágil
23. `src/extractors/energia_ocr.py:45-72` — Regex `(\d{2,4})\s*[Kk][Ww][Hh]` não casa com OCR distorcido (`kwhh`, `khwh`, `kWHh`). Validação `if mes_match and valor_match` aceita consumo = 0. Histórico CLAUDE.md confirma 67% de precisão em kWh (R$ 100% ok).

### P1 — Holerites fora de {G4F, Infobase} caem silenciosamente
24. `src/intake/registry.py:76-84` — `_ASSINATURAS_HOLERITE` lista marcadores específicos das duas empresas. Se Vitória receber holerite novo (outra fonte) ou André trocar de emprego, o pipeline classifica errado ou pula com warning baixo.

### P2 — Anti-duplicação só varre `_classificar/`
25. `src/intake/dedup_classificar.py:58` — Pasta hardcoded; arquivo duplicado em `data/raw/<pessoa>/<banco>/` não é detectado. Se o banco regenera o extrato com timestamp diferente, vira duplicata semântica que escapa.

### P2 — Parsing BR fragmentado em 22 extratores
26. `src/utils/parse_br.py` cobre **valor** (`parse_valor_br`), **não cobre data** brasileira. Cada extrator (`danfe_pdf.py:53`, `energia_ocr.py:53`, etc.) faz seu próprio regex. Sprint INFRA-parse-br virou sub-sprint mas data ainda fragmentada.

### P3 — Holerite sem `codigo_produto` não cria edge `contem_item`
27. `src/graph/ingestor_documento.py:563` — Skip se `not item.get("codigo")`. Holerites têm verbas (Salário base, INSS, IRRF, VR) sem código do produto → impossível drill-down item-a-item em renda.

### P3 — 99,7% testes sintéticos
28. 1.987 testes versus apenas **6 fixtures reais** em `tests/fixtures/` (PDF/PNG/XML). Replicação do bug-Sprint-55 (1.761 transações classificadas erradas, pytest não pegou): risco real continua. Mitigação atual é o smoke aritmético, mas só 6 contratos verdadeiros (ver §3).

---

## §3 — Integração, bugs e ADRs órfãs

### P0 — ADR-08 (Supervisor-Aprovador LLM) tem 0% de implementação desde 2025
29. `docs/adr/ADR-08-supervisor-aprovador.md` aprovada e detalhada; nenhum dos seguintes existe:
   - `src/llm/supervisor.py` — pasta `src/llm/` não existe.
   - `pyproject.toml:13-28` — sem `anthropic` em deps.
   - `mappings/proposicoes/` — diretório não existe.
   - `cost_tracker.py` / `data/output/llm_costs.sqlite` — não existem.

### P0 — Anti-órfão na inbox sem cobertura — perda silenciosa de dados
30. Mecanismo de linking existe (`src/graph/linking.py`, 26 referências a `documento_de`), mas **não há monitor** de "arquivo entrou em `data/raw/` ou `data/raw/_classificar/` há > 24h e nunca produziu aresta `documento_de`". Sem alerta, sem relatório, sem sprint formal disparada.

### P0 — Mobile bridge não-auditado
31. `Protocolo-Mob-Ouroboros` espera que o backend leia `vault/daily/`, `vault/eventos/`, `vault/inbox/mente/{humor,diario}/`, `vault/treinos/`, `vault/medidas/` e gere `vault/.ouroboros/cache/{financas,humor-heatmap}.json`. **Nenhum código no backend faz isso hoje.** APK em desenvolvimento vai bater na parede quando precisar destes caches.

### P0 — Vault Obsidian sem monitoração de dessincronia
32. `src/obsidian/sync_rico.py` (611 linhas) confia no hash de conteúdo + tag `#sincronizado-automaticamente`. Mas grep não encontrou uso real da tag em arquivos `.md` versionados; sem alerta se uma nota foi editada manualmente sem a tag e o backend a sobrescreve.

### P1 — ADRs adjacentes também sem implementação
33. **ADR-09** (autossuficiência progressiva), **ADR-10** (resiliência a dados incompletos), **ADR-11** (classificação em camadas), **ADR-12** (cruzamentos via grafo) — todos arquivos `.md` aprovados, sem código equivalente claro. ADRs aceitas que viraram decoração.

### P1 — Sprint 87 declarada concluída com 10 sub-tasks abertas
34. `docs/sprints/concluidos/sprint_87_ressalvas_claude_debitos_tecnicos.md` lista 10 dependências não-feitas (boleto_pdf novo, MOC mensal, reconciliação boleto↔transação, drill-down em mais plots, etc.). Cada uma deveria ser sprint-filha formal; nenhuma foi criada.

### P1 — Sprint 87d com 6 propostas órfãs em `docs/propostas/extracao_cupom/`
35. Sprint declarou explicitamente "limpeza é trabalho manual pós-sprint" — débito operacional não fechado.

### P1 — Métrica de testes diverge
36. `pytest --collect-only -q | tail -1` retorna **2.028**. CLAUDE.md e ESTADO_ATUAL.md declaram **1.987 passed / 9 skipped / 1 xfailed**. Delta de 41 testes não reconciliados. Ou 41 testes não rodam (skip silencioso) ou a documentação está atrasada.

### P1 — Integrações declaradas mas inexistentes
37. CLAUDE.md menciona "Belvo (em teste), Gmail (setup pendente)". Em `src/integrations/`: `controle_bordo.py`, `gmail_csv.py`, `belvo_sync.py`, `__init__.py`. **Não existem**: `google_calendar.py`, `thunderbird_email.py`, `thunderbird_ics.py`, `assinaturas_detector.py`. Capacidades prometidas no contexto do dono não cobertas.

### P2 — `run.sh --reextrair-tudo` sem teste de idempotência
38. Modo destrutivo com confirmação `--sim` (Sprint AUDIT-MENU-CONFIRMACAO), mas zero teste de "rodar 2x ⇒ grafo não dobra". Risco de duplicação silenciosa.

### P2 — Smoke aritmético declara 8 contratos mas só 6 implementados
39. `scripts/smoke_aritmetico.py` — grep encontrou 6 funções `contrato_*`. Documento declara 8. Invariante crítico **ausente**: "soma de receita_total no `resumo_mensal` == soma de `tipo=Receita` no `extrato`".

### P2 — Arquivos > 800 linhas violando CLAUDE.md
40. `src/dashboard/tema.py` (1.191L), `src/graph/ingestor_documento.py` (940L), `src/dashboard/paginas/revisor.py` (888L), `src/dashboard/dados.py` (830L). Limite documentado em CLAUDE.md §convenções; sem refatoração.

### P3 — Hooks git só locais
41. `.git/hooks/{pre-commit,pre-push,commit-msg}` ok, mas em fresh clone o setup depende de `install.sh` (não auditado). CLAUDE.md ARMADILHA #9 alerta — sem documentação de bootstrap atualizada.

### P3 — Pyvis com versão flutuante
42. `pyproject.toml:49` — `pyvis>=0.3` sem upper-bound nem lock file. Atualização automática pode quebrar grafo.

### P3 — PII versionada — risco mitigado mas sem garantia
43. Grep com regex CPF/CNPJ não retornou matches fora de `data/`, `mappings/`. Sprint 99 (redactor PII em logs INFO) ainda em backlog. Risco baixo, mas sem teste automatizado.

---

## §4 — Documentação

### P1 — CLAUDE.md em conflito com a realidade do repo
44. CLAUDE.md header declara **VERSÃO 5.10**, **TRANSAÇÕES 6.094**, **TESTES 1.987**. Pytest hoje: 2.028. Várias seções repetem "Fase NU completa" mas o mesmo arquivo lista P1 ainda pendentes (Sprint 99, 100). Documento de contrato vivendo dois estados.

### P1 — `contexto/PROMPT_NOVA_SESSAO.md` aponta ordem de leitura desatualizada
45. Recomenda `docs/AUDITORIA_2026-04-26.md` como ponto principal, mas a auditoria mais recente é `docs/AUDITORIA_2026-04-29_self.md` (4-way). Fluxo de onboarding manda uma sessão fresca para o lugar errado primeiro.

### P2 — Sprint specs em `docs/sprints/concluidos/` sem campo de "data de conclusão"
46. Várias specs concluídas não registram quando fecharam (só commit do git). Auditoria forense precisa cruzar com `git log` para descobrir cronologia. Um campo `concluida_em: YYYY-MM-DD` no frontmatter resolveria.

### P3 — ADR-21 (fusão Ouroboros + Controle de Bordo) sem follow-up
47. ADR aprovada em 2026-04-26 propondo fusão de longo prazo. Não há ADR-22 ou ADR-23 detalhando próximos passos. Decisão estratégica fica órfã do roadmap.

---

## §5 — Resumo agregado

| Severidade | Total |
|---|---|
| **P0** (bloqueia uso real) | **9** achados (4 UI + 3 extração + 4 integração) — itens 1–4, 19–21, 29–32 |
| **P1** (degrada experiência) | **13** achados — itens 5–6, 22–24, 33–37, 44–45 |
| **P2** (funcionalidade incompleta) | **15** achados — itens 7–14, 25–26, 38–40, 46 |
| **P3** (cosmético/observabilidade) | **9** achados — itens 15–18, 27–28, 41–43, 47 |
| **Total honesto** | **46 falhas reais** identificadas com arquivo:linha |

**Resposta direta ao "o que falta pro projeto estar finalizado":** as 9 P0 são bloqueio claro. As 13 P1 são o que separa "funciona mas chateia" de "central de vida adulta de verdade". As P2/P3 são higiene contínua. Sem fechar P0+P1 (22 itens), o projeto **não está finalizado**, mesmo com 1.987 testes passando.

---

# PARTE II — PLANO DE FECHAMENTO (consolidado por área)

Este plano fecha **todos os 46 achados** acima, agrupados em 6 ondas executáveis. Ordem de ataque otimizada por bloqueio cruzado.

## Onda 1 — Anti-migué + restaurar débitos abertos (~25h)
Endereça itens 11, 14, 16, 30, 34, 35, 36, 38, 39, 40, 41, 42, 44, 45, 46.

| Sprint | O que faz | Itens fechados |
|---|---|---|
| ANTI-MIGUE-01 | `tests/conformance/4way_gate.py` + `make conformance-<tipo>` (≥3 amostras 4-way) | infraestrutura para Onda 3 |
| ANTI-MIGUE-02 | `src/intake/anti_orfao.py` + relatório `output/orfaos.md` + alerta sprint automática | 30, 38 |
| ANTI-MIGUE-03 | Reconciliar 1.987 vs 2.028 testes; investigar 41 testes "fantasma" | 36 |
| ANTI-MIGUE-04 | Completar smoke aritmético: 6 → 8 contratos; novo: `receita_total_resumo == receita_extrato` | 39 |
| ANTI-MIGUE-05 | Fechar Sprint 87d: UUID → hash determinístico em fallback supervisor cupom | 35 |
| ANTI-MIGUE-06 | Fechar Sprint 87 (10 sub-tasks → 10 sprints-filhas formais) | 11, 34 |
| ANTI-MIGUE-07 | Sincronizar CLAUDE.md, ESTADO_ATUAL.md, PROMPT_NOVA_SESSAO.md com estado real | 44, 45 |
| ANTI-MIGUE-08 | Refatorar 4 arquivos > 800 linhas | 40 |
| ANTI-MIGUE-09 | `tests/test_run_sh_idempotente.py` para `--reextrair-tudo` | 38 |
| ANTI-MIGUE-10 | Documentar bootstrap em `install.sh` + `docs/BOOTSTRAP.md` | 41 |
| ANTI-MIGUE-11 | Pinar `pyvis<1.0` em `pyproject.toml` + lock file | 42 |
| ANTI-MIGUE-12 | Frontmatter `concluida_em: YYYY-MM-DD` em sprints concluídas | 46 |

## Onda 2 — ADR-08 vivo + ADRs adjacentes (~30h)
Endereça itens 29, 33.

| Sprint | O que faz |
|---|---|
| LLM-01 | `src/llm/{__init__,supervisor,cost_tracker}.py` + `anthropic` em deps + cache LRU |
| LLM-02 | `supervisor.propor_extractor()` quando classifier=None → spec auto em `backlog/sprint_extractor_<tipo>.md` |
| LLM-03 | `supervisor.propor_regra()` para fornecedor frequente sem regra → `mappings/proposicoes/` |
| LLM-04 | `supervisor.auditor()` (Modo 2) — audita N% de classificações, relatório quinzenal |
| LLM-05 | UI no Revisor 4-way para aceitar/rejeitar/modificar proposições LLM |
| LLM-06 | SHA-guard: proposta rejeitada com mesmo hash não volta |
| LLM-07 | Métricas de autossuficiência (ADR-09) — % determinístico vs LLM no dashboard |

## Onda 3 — Cobertura documental universal (~40h)
Endereça itens 19, 20, 21, 22, 23, 24, 25, 26, 27.

| Sprint | Tipo novo |
|---|---|
| DOC-01 | extrator_amazon_pedido (HTML+PDF, com itens granulares) |
| DOC-02 | extrator_mercado_nf_fisica (Vivendas + similares com itens) |
| DOC-03 | extrator_carteira_estudante (JPEG/PDF + validade) |
| DOC-04 | extrator_cnh + alerta de validade |
| DOC-05 | extrator_rg |
| DOC-06 | extrator_diploma |
| DOC-07 | extrator_historico_escolar (com CR + grade) |
| DOC-08 | extrator_certidao_nascimento |
| DOC-09 | extrator_exame_medico |
| DOC-10 | extrator_receita_medica_v2 (registry-driven, fechando #22) |
| DOC-11 | extrator_plano_saude_carteirinha (ANS) |
| DOC-12 | extrator_govbr_pdf (auto-detecta qualquer PDF gov.br) |
| DOC-13 | `src/intake/multi_foto_selector.py` (item 20) — Laplaciano + OCR confidence |
| DOC-14 | `src/intake/anti_duplicacao_semantica.py` — cobre `data/raw/` inteiro (item 25) |
| DOC-15 | `src/utils/parse_br.py` ganha `parse_data_br()` + remove regex local de 22 extratores (item 26) |
| DOC-16 | `src/extractors/danfe_pdf.py:224` — validar ingestão antes de retornar (item 21) |
| DOC-17 | OCR energia com cleanup pré-regex (item 23) |
| DOC-18 | `_ASSINATURAS_HOLERITE` declarativa em YAML + supervisor LLM detecta novo holerite (item 24) |
| DOC-19 | Holerite cria edge `contem_item` mesmo sem `codigo_produto` (item 27) |

Cada extrator fecha apenas com gate 4-way ≥3 amostras (ANTI-MIGUE-01).

## Onda 4 — Cruzamento micro + IRPF (~20h)
Endereça itens 27, 28 (mitigação).

| Sprint | O que faz |
|---|---|
| MICRO-01 | Edges `transacao→nfce→item` no grafo em runtime |
| MICRO-02 | `mappings/items_canonicos.yaml` (balinha, leite, pão → categoria final) |
| MICRO-03 | Página `cruzamento_micro` no dashboard — drill-down item-a-item (Vivendas R$ 800 → R$ 40 balinha) |
| IRPF-01 | Botão "Gerar pacote IRPF 2026" → ZIP com NFs, holerites, transações, parcelamentos, DAS, comprovantes médicos |
| IRPF-02 | Link automático receita médica + exame + pagamento bancário (dedutível) |

## Onda 5 — Mobile bridge + fontes adicionais (~25h)
Endereça itens 31, 37.

| Sprint | O que faz |
|---|---|
| MOB-01 | `src/intake/vault_bridge.py` — backend lê `.md` do mobile e roteia (item 31) |
| MOB-02 | `src/cache/mobile_cache.py` gera `vault/.ouroboros/cache/{financas,humor-heatmap}.json` |
| MOB-03 | Refactor PESSOA_A/PESSOA_B + `mappings/pessoas.yaml` (paridade com mobile) |
| FONTE-01 | `src/integrations/google_calendar.py` (sync `.ics`) |
| FONTE-02 | `src/integrations/thunderbird_email.py` (lê maildir local, roteia anexos para inbox) |
| FONTE-03 | `src/integrations/thunderbird_ics.py` (calendars locais) |
| FONTE-04 | `src/analysis/assinaturas.py` — recorrência (mesma data ±3d, valor ±5%, ≥3 ocorrências) |

## Onda 6 — UX/UI + OMEGA (~30h)
Endereça itens 1–10, 12–13, 15, 17–18, 32, 47.

| Sprint | O que faz | Itens |
|---|---|---|
| UX-01 | Migrar 4 arquivos `st.error/warning/info/success` → `callout_html` | 1–4 |
| UX-02 | Treemap WCAG-AA em viewport ≤1200px + heatmap com fundo Dracula | 5, 6 |
| UX-03 | Drill-down Sankey + heatmap + bar Pagamentos + line Projeções + bar Completude | 7–11 |
| UX-04 | Revisor responsivo + scroll/expand para documentos com 50+ itens | 12, 13 |
| UX-05 | Pyvis fallback decente (spinner, timeout, mensagem útil) | 15 |
| UX-06 | Coluna "Doc?" com observabilidade (logs estruturados em falhas do grafo) | 16 |
| UX-07 | Snapshot histórico com timestamp dinâmico em Inventário/Prazos/Dívidas Ativas | 17 |
| UX-08 | Cobertura de teste deep-link `?tab=` em todas 13 abas + 5 clusters | 18 |
| UX-09 | Cleanup 6 docstrings com acentuação quebrada (`# noqa: accent` válidas ficam) | 14 |
| OMEGA-94a | Aba Saúde (receitas, exames, plano + alertas validade) | OMEGA |
| OMEGA-94b | Aba Identidade (RG/CNH/passaporte + alertas) | OMEGA |
| OMEGA-94c | Aba Profissional (contratos, registrato, rescisão) | OMEGA |
| OMEGA-94d | Aba Acadêmica (diplomas, históricos, certificados) | OMEGA |
| ADR-23 | Fusão Ouroboros + Controle de Bordo — próximos passos pós-ADR-21 | 47 |
| MON-01 | Vault Obsidian: monitor de dessincronia + alerta de tag faltando | 32 |

**Total:** ~170h ≈ 21 dias úteis intensos / 7-8 semanas em ritmo sustentável.

---

# PARTE III — Mecanismo anti-migué consolidado

Para CADA sprint, antes de mover de `backlog/` para `concluidos/`:

1. **Hipótese declarada e validada com grep** (CLAUDE.md regra empírica).
2. **Proof-of-work runtime-real** capturado em log.
3. **Quando aplicável: gate 4-way ≥3 amostras** (`make conformance-<tipo>`).
4. **`make lint` exit 0**.
5. **`make smoke` 8/8** (depois da Onda 1, contratos completos).
6. **pytest baseline mantida ou crescida**.
7. **Achados colaterais viraram sprint-ID OU Edit-pronto** — zero "TODO depois".
8. **Validador (humano ou subagent) APROVOU** — sem auto-aprovação.
9. **Spec movida com frontmatter `concluida_em: YYYY-MM-DD`**.
10. **Linha em `VALIDATOR_BRIEF.md` rodapé** registrando o padrão canônico (se aplicável).

`scripts/check_anti_migue.sh` (a criar em ANTI-MIGUE-XX) automatiza checks 1–9 e bloqueia o `git mv` da spec sem todos verdes.

---

# PARTE IV — Verificação fim-a-fim

Plano só está "executado de verdade" quando:

1. `make smoke` 8/8 com **8 contratos reais** (não 6).
2. `make lint` exit 0.
3. `pytest tests/ -q` ≥ 1.987 + N novos, sem skip silencioso de 41 testes.
4. `make anti-migue` exit 0 (todos os 9 checks por sprint concluída).
5. `make conformance-<tipo>` exit 0 para todos os tipos da Onda 3 (≥3 amostras 4-way cada).
6. `./run.sh --full-cycle` executa anti-órfão e gera mobile-cache sem erro.
7. `./run.sh --dashboard` exibe abas novas: Cruzamento Micro, Saúde, Identidade, Agenda, Acadêmica.
8. **Sessão humana via Revisor 4-way** valida ≥3 amostras de cada novo tipo.
9. **Pacote IRPF 2025** gerado on-demand com 100% das fontes vinculadas.
10. **Mobile bridge:** subir `.md` em `vault/daily/` no celular → backend captura no próximo `--full-cycle` → cache JSON gerado → mobile lê tela 22 (Mini Financeiro) com dado novo.
11. **Anti-órfão:** colocar PDF arbitrário em `data/raw/_classificar/` → 24h depois há sprint formal aberta automaticamente OU integração concluída.
12. **Multi-foto:** subir 3 fotos da mesma NF → 1 transação no XLSX, não 3.

---

# PARTE V — O que este plano explicitamente NÃO faz

- Não toca em código nesta sessão (plan mode).
- Não cria as 50+ specs em `docs/sprints/backlog/` ainda — fica para a primeira sessão de execução.
- Não escolhe entre Syncthing e Obsidian Sync — herda decisão do Mob-Ouroboros.
- Não rebatiza o projeto (Sprint 83 fica em backlog).
- Não inclui análise de burnout/finanças do casal (regra explícita: foco técnico).
- Não implementa F-14 a F-17 do mobile (v2 mobile).

---

*"Saber onde estamos é metade do caminho. Saber o que ainda falta é a outra metade. Saber que falta é não-aceitar declarar 'pronto' antes do gate 4-way bater 100%." — princípio do snapshot honesto*
