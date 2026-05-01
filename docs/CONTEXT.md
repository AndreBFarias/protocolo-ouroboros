# CONTEXT.md — Contexto humano + operacional do projeto

**Data:** 2026-04-21
**Fonte:** sessão de auditoria profunda em que o Andre compartilhou a visão real do projeto. Este documento preserva o contexto humano que motiva as decisões de design. Qualquer executor-sprint, validador ou IA que retomar o projeto deve ler este arquivo antes de qualquer ação.

**Regra:** nada aqui é ficção. Tudo foi declarado pelo Andre durante a sessão 2026-04-21.

---

## 1. As pessoas

### Andre Farias
- **Profissão:** Analista/Engenheiro de Dados, sênior em Python. Poderia construir tudo isso sozinho — mas tem duas jornadas de trabalho simultâneas.
- **Trabalhos atuais** (cumulativos):
  - MEC via G4F (contractor federal) — ver `Controle de Bordo/Trabalho/Andre/G4F/`
  - Energisa — ver `Controle de Bordo/Trabalho/Andre/Energisa/`
- **Anterior:** Infobase (saiu em 2024-03).
- **Máquina principal:** `nitro-5` (Pop!_OS, Acer Nitro 5).
- **Bancos:** Itaú, Santander, C6, Nubank (cartão + conta).
- **Saúde:** TDAH. Usa Venvanse — **prescrição é 1 comprimido de 70mg/dia**, mas está tomando 2. Ciente que é errado.
- **Acompanhamento psiquiátrico:** Clínica Ludens. Essa é a origem dos gastos com "Saúde" / "Farmácia" no extrato — precisam tracking documental para IRPF.
- **Rotina:** ~16 horas de trabalho por dia. Sem exercício, pouca comida caseira, estresse alto. Ciente que essa é uma rota auto-destrutiva.
- **Estado financeiro:** apesar dos dois trampos, dívidas **crescendo** (maior do que quando tinha só um emprego). Ciclo sem fim.
- **Decisão consciente:** quer sair da Energisa **de forma sistemática, organizada**, não abrupta. Este projeto é a ferramenta de clareza pra conseguir fazer isso.

### Vitória Maria Silva dos Santos
- **Profissão:** Bolsista NEES/UFAL (~R$ 3.700/mês).
- **Trabalho:** diretamente no MEC. Projetos: Projeto Mulher.
- **Bancos:** Nubank PF (conta 97737068-1), Nubank PJ (conta 96470242-3).

### Relação
- Casal. Compartilham despesas, apartamento, metas. Vault `~/Controle de Bordo/` é hub único do casal.
- Dívidas Nubank da Vitória (PF R$ 13.049 + PJ R$ 10.783) — decisão consciente: **deixar caducar**, prescrição em set/2030.

---

## 2. Gastos recorrentes conhecidos (ground truth)

Informações que o Andre compartilhou sobre o que é o quê na base de dados:

| Padrão no extrato | Realidade | Categoria correta |
|---|---|---|
| Padaria Ki-Sabor, R$ 800-900 | **Aluguel do apartamento** (paga pro proprietário, que tem padaria) | Aluguel (Obrigatório) |
| Clínica Ludens | Psiquiatra | Saúde (Obrigatório) |
| Sesc (várias formas) | Natação | Natação (Obrigatório) |
| Neoenergia | Conta de luz | Energia (Obrigatório) |
| CAESB | Água | Água (Obrigatório) |
| Claro | Internet | Internet (Obrigatório) |
| iFood frequente | Delivery — "o tanto de idiotice que pago" | Delivery (Supérfluo) |

---

## 3. A visão real do projeto (declaração do Andre)

> "vc vai criar o sistema, integrar ele, avaliar cada output, gerar as perguntas que precisa pra mim de forma que possamos ter uma central de tudo, nesse primeiro momento é a gestão financeira"

> "vou colocar recibos em pdf, ofx, excel, csv, png e imagens, eu quero que vc construa automações pra ir organizando tudo que temos ali"

> "Renomear cada arquivo, colocar eles na pasta, extrair todas as informações, preservar os originais, anexar os dados extraídos, colocar no nosso banco de dados local, de forma que tenhamos o histórico completo"

> "com isso eu e vc consigamos ter uma clareza total da minha vida financeira. De tudo que tá errado. Olha o tanto de remédio psiquiátrico, o tanto de ifood, o tanto de idiotice que eu pago."

> "vou gastando uma nota com IA, sendo que modéstia parte eu sou sênior em python eu poderia fazer mas dois trampos cobram demais o preço"

> "Aí vivo no ciclo sem fim, sem praticar exercícios, sem ter tempo de fazer comida, me estresso por ficar 16h trampando e claramente isso vai me matar"

> "fiz muita merda. Uso do Venvanse da forma errada (2 cp de 70, mesmo comigo tendo tdah e podendo somente tomar um cp)"

> "agora quero que apenas faça um trabalho manual, com carinho me ajuda a sair dessa"

O projeto não é apenas técnico. É ferramenta de sobrevivência.

---

## 4. Workflow desejado (ciclo canônico)

```
1. Andre tira foto de boleto OU joga PDF/CSV na inbox (do Controle de Bordo)
2. Roda ./run.sh
3. Sistema:
   - extrai os textos
   - tabula
   - renomeia canonicamente
   - move pras pastas corretas
   - gera as tags
   - gera o trackeamento
   - popula o grafo
4. Sistema pergunta: abrir dashboard? gerar relatório? ambos? nada?
5. Andre vê o estado
6. Se quiser análise profunda: leva relatório .md pro Claude online
```

Requisitos explícitos que o Andre listou:

- **Dashboard 100% interativo**: clicar em qualquer ponto de gráfico navega para extrato filtrado.
- **Tracking transação↔documento**: clicar em "Natação André" abre boleto + recibo.
- **Grafo estilo Obsidian**: tudo linkado, filtro por anexos/tags/órfãos, clicar navega.
- **Filtro forma de pagamento** na sidebar (abaixo da granularidade).
- **Gap analysis**: "lista cada documento de cada mês do que tiver faltando, cada coisinha minúscula".
- **Workflow via run.sh com menu** pergunta ações pós-processamento.

---

## 5. Integração com Controle de Bordo

### O que JÁ existe no `~/Controle de Bordo/` (vault Obsidian)

- Estrutura PARA: `Pessoal/`, `Trabalho/`, `Projetos/`, `Conceitos/`, `Diario/`, `Inbox/`, `Arquivo/`.
- Motor Python próprio em `.sistema/scripts/`:
  - `inbox_processor.py` — orquestrador da inbox do vault
  - `content_detector.py` — detecção de conteúdo textual
  - `ocr_detector.py` — OCR em documentos
  - `document_creator.py` — cria notas a partir de detecções
  - `similarity_grouper.py` — agrupa notas similares
  - `emoji_guardian.py` — bloqueia emojis
  - `health_check.py` — saúde do vault
  - `export_to_other_devices.py` — sync entre devices
- Config canônico `.sistema/config/`:
  - `devices.yaml` — mapeamento hostname → autor (preenche frontmatter automático)
  - `protegidos.yaml` — arquivos que não podem ser movidos
  - `regras.yaml` — regras de classificação
- Comandos shell: `vsync`, `vquick`, `vhealth`, `vstats`, `vsize`.
- Sync Obsidian com limite 1GB (por isso `Arquivo/` está em `.syncignore`).
- Pastas relevantes pro Ouroboros:
  - `Pessoal/Casal/Financeiro/` — destino dos outputs do Ouroboros
  - `Pessoal/Casal/Contas/`, `Pessoal/Casal/Notas Fiscais/`
  - `Pessoal/Documentos/` — documentos pessoais (RG, CV, contratos, apólices, planos) — **FORA do escopo do Ouroboros por enquanto**

### Contrato de coabitação (ADR-18)

| Domínio | Dono |
|---|---|
| Inbox (captura física) | Compartilhada: ambos motores leem |
| Processamento de docs financeiros (OFX, CSV bancário, PDF extrato, DANFE, NFC-e, XML NFe, cupom térmico, receita médica, cupom garantia, holerite, boleto, conta luz, conta água) | **Ouroboros** |
| Processamento de notas pessoais, docs genéricos | **Motor do vault** |
| Preservação do original | **Ouroboros** sempre copia para `data/raw/originais/{hash}.ext` antes de mover |
| Arquivo original no vault após processamento | **Ouroboros** copia para `Pessoal/Casal/Financeiro/_Attachments/` |
| `.sistema/`, `Trabalho/`, `Segredos/`, `Arquivo/` | Off-limits para Ouroboros |

---

## 6. Decisões confirmadas nesta sessão

1. ~~**Mapeamento de output no vault:** `Pessoal/Casal/Financeiro/{Documentos/{YYYY-MM}/, Fornecedores/, Meses/, _Attachments/}` — ACEITO implicitamente.~~ **Aguarda confirmação explícita (pendência VISAO_UNIFICADA §Pendências #1).**
2. **Docs pessoais (RG, CV, apólices):** **FICAM FORA** do Ouroboros por enquanto. Controle de Bordo gerencia. (Confirmado 2026-04-21.)
3. **Logo:** já existe em `assets/icon.png` (724x733 PNG RGBA). Sprint 76 atualizada.
4. **Rename para Title Case:** pasta local + repo GitHub viram `Protocolo Ouroboros` / `Protocolo-Ouroboros` (Sprint 83).
5. **Documentos irrecuperáveis:** categoria nova (`irrecuperavel`). Boletos antigos removidos do site do fornecedor entram aí. Contagem separada no gap analysis. (ADR-20 + Sprint 85.)

---

## 7. Escala de modelos acordada

- **Opus (esta sessão)**: planejar, redigir ADRs/specs, validar, conversar com o Andre.
- **Sonnet** (padrão do `executor-sprint`): executar sprints.
- **Haiku**: apenas higiene trivial (lint sweep, mover arquivo, fix noqa em 1 linha).

Justificativa: Haiku não dá conta de executor-sprint (multi-arquivo + evidência visual + proof-of-work). Sonnet é o sweet spot. Opus só pra sessões onde o custo vale (planejamento profundo).

---

## 8. Princípios operacionais (invioláveis)

1. **Evidência empírica > hipótese do planejador** (meta-regra 6). Antes de mudar identificador, `rg` pra confirmar. Se não casa, reportar divergência com dados.
2. **Zero follow-up acumulado** (meta-regra 7). Achado colateral vira sprint-nova OU Edit pronto. Nunca "issue depois".
3. **Validação runtime-real obrigatória** (check #1). `./run.sh --check` + `make smoke` (Sprint 56) + screenshot via Playwright quando UI.
4. **Preservação do original** (ADR-18). Nenhum arquivo mexido sem cópia em `data/raw/originais/`.
5. **Acentuação PT-BR correta em prosa humana** (CLAUDE.md). Identificadores técnicos N-para-N com schema do grafo aceitam ASCII via `# noqa: accent`.
6. **Zero emojis** em código, commits, docs. Zero menções a IA em commits.

---

## 9. Arquivos físicos já preparados pelo Andre (golden tests)

Ver `docs/GOLDEN_TEST_CASES.md` para detalhes. Resumo:

| Path | Conteúdo | Sprint alvo |
|---|---|---|
| `inbox/natacao_andre.pdf` | Boleto Sesc (mensalidade) | 70 + 74 |
| `inbox/natacao_andre2.pdf` | Boleto Sesc (outra mensalidade) | 70 + 74 |
| `inbox/notas de garantia e compras.pdf` | Multi-doc de notas fiscais + garantia | 70 + 47b |
| `inbox/extrato dos debitos.pdf` | Extrato bancário PDF | 70 + extrator correspondente |
| `~/Controle de Bordo/Pessoal/Documentos/*.pdf` | Docs pessoais do Andre (CV, contratos, apólices, plano saúde, RG) | **FORA do escopo** |
| `data/raw/andre/holerites/document(N).pdf` | 40+ holerites G4F/Infobase com nomes ruins | 85 (XLSX faltantes) |

---

## 10. Estado do pipeline no fim desta sessão (2026-04-21)

### Métricas reais (pós-sprints 55-69, 68b)

- XLSX `ouroboros_2026.xlsx`: 6.086 transações, 82 meses.
- Grafo SQLite: 7.421 nodes + 24.584 edges.
- Smoke aritmético: **8/8 contratos OK** via `make smoke`.
- Testes: 894 passed, 10 skipped, 0 failed.
- Lint: `make lint` exit 0.

### Receita abril/2026 (evolução)

| Estado | Valor | Observação |
|---|---|---|
| Antes Sprint 55 | R$ 9.939,24 | Contaminada por juros/IOF/multa/transf enviada como "Receita" |
| Após Sprint 55 | R$ 7.963,49 | Bug estrutural do classificador de tipo corrigido |
| Após Sprint 68b | R$ 15.622,00 | 316 TIs falsos-positivos reclassificados; MAS ~280 TIs legítimas caíram como Receita (achado 68b-A) |
| Esperado após Sprint 82 | < R$ 13.000 | Canonicalizer variantes curtas captura variantes "Vitória abreviado" etc. |

### Completude documental no grafo

- Documentos: 2 (só NFC-e Americanas)
- Itens: 33
- Edges `pago_com/confirma/comprovante`: 0 (Sprint 74 resolve)
- Edges `prescreve_cobre` / `mesmo_produto_que`: 0 (precisa volume real — Sprint 57 foi honesta sobre isso)

---

## 11. Pendências para a próxima janela

1. Andre confirma mapeamento `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}` no vault — ou prefere outro layout?
2. Andre confirma consumir `~/Controle de Bordo/Inbox/` direto, ou quer subpasta `Inbox/financeiro/` dedicada?
3. Andre preenche CPFs no `mappings/contas_casal.yaml` (hoje tem placeholders `<CPF_ANDRE>` e `<CPF_VITORIA>`).
4. Decisão sobre Opção A vs B na Sprint 81 (scripts/ dentro do lint ou opt-out).

---

## 11.5. Caches Mobile (Sprint MOB-bridge-2)

O backend gera dois arquivos JSON readonly em `~/Protocolo-Ouroboros/.ouroboros/cache/`
durante `make sync` (alias de `./run.sh --full-cycle`). O app Mobile
**só lê** esses arquivos — ADR cruzada
`Protocolo-Mob-Ouroboros/docs/ADRs/0012-cache-mobile-readonly.md`.

- `humor-heatmap.json` — alimenta a Tela 21 (Mini Humor). Cobre 90
  dias retroativos com células `(data, autor, humor, energia,
  ansiedade, foco)` agregadas a partir de `daily/` e
  `inbox/mente/humor/` no Vault. Estatísticas `media_humor_30d`,
  `registros_30d`, `registros_total` por pessoa.
- `financas-cache.json` — alimenta a Tela 22 (Mini Financeiro).
  Semana ISO atual com `gasto_semana`, `gasto_semana_anterior`,
  `delta_textual` (heurística vs média de 12 semanas), top 5
  categorias com percentual, 20 últimas transações.

Geração via `python -m src.mobile_cache` (também invocado pela flag
`--mobile-cache` standalone em `run.sh` quando se quer regenerar
caches sem rodar o pipeline ETL inteiro). Escrita atômica via
`.tmp` + `os.replace` garante que o leitor SAF do Mobile jamais
observe arquivo parcial. Schema versionado via campo
`schema_version: 1` (mudança de shape exige ADR sucessor).

---

## 12. Referências cruzadas

- `docs/VISAO_UNIFICADA.md` — mapa inteiro das fases e sprints.
- `docs/GOLDEN_TEST_CASES.md` — casos de teste reais do ambiente.
- `docs/ROADMAP.md` — estado atual + caminho crítico.
- `CLAUDE.md` — regras invioláveis + schema do XLSX.
- `VALIDATOR_BRIEF.md` — checks do validador + histórico das sprints.
- `docs/adr/ADR-18..20-*.md` — as 3 decisões arquiteturais da sessão 2026-04-21.

---

*"Código que não pode ser entendido não pode ser mantido. Projeto que não pode ser lembrado não pode ser retomado."*
