# ADR-18 — Integração com Controle de Bordo (vault Obsidian canônico)

**Status:** PROPOSTO (aguarda aprovação do Andre)
**Data:** 2026-04-21
**Contexto:** Sessão de auditoria profunda 2026-04-21, após o Andre compartilhar a visão real do projeto.

## Contexto

O projeto Protocolo Ouroboros nasceu como pipeline ETL financeiro local. Em paralelo, o Andre mantém o `~/Controle de Bordo/`, um vault Obsidian maduro com:

- Estrutura PARA (Pessoal, Trabalho, Projetos, Conceitos, Diario, Inbox, Arquivo).
- Motor inteligente em `.sistema/scripts/` (`inbox_processor.py`, `content_detector.py`, `ocr_detector.py`, `document_creator.py`, `similarity_grouper.py`, `emoji_guardian.py`, `health_check.py`, `export_to_other_devices.py`).
- Config canônico em `.sistema/config/` (`devices.yaml` para autor automático por hostname, `protegidos.yaml` para arquivos críticos, `regras.yaml`).
- Pastas `Pessoal/Casal/` com subestrutura já preparada: `Contas/`, `Financeiro/`, `Notas Fiscais/`, `Saude/`, `Tasks/`, `Eventos/`, `Metas/`.
- Documentos pessoais em `Pessoal/Documentos/` (CV, contratos, apólices, RG, plano de saúde, etc.).
- Inbox ativa em `Inbox/` (captura rápida, processada pelo motor do vault).
- Sync do próprio vault via `vsync`, `vquick`, `vhealth`.

O Protocolo Ouroboros TAMBÉM tem seu próprio `src/inbox_processor.py`, seu próprio `data/raw/`, seu próprio sync Obsidian (Sprint 06, unidirecional pobre). **Há duplicação e o Andre hoje precisa pensar em dois sistemas separados.** A visão declarada é unificar.

## Decisão

**O vault Controle de Bordo é a fonte da verdade para documentos e inbox humana. Protocolo Ouroboros é o motor ETL financeiro que consome da inbox unificada e escreve no vault.**

### Contratos canônicos

1. **Inbox unificada:** `~/Controle de Bordo/Inbox/` passa a ser o único ponto de entrada. O Andre joga tudo ali — foto de boleto, PDF de NFe, CSV bancário, apólice, recibo, voucher.

2. **Divisão de responsabilidades por tipo:**
   - **Não-financeiro** (CV, foto, documento pessoal): motor do vault (`~/Controle de Bordo/.sistema/scripts/inbox_processor.py`) processa e move para pasta correspondente em `Pessoal/Documentos/`.
   - **Financeiro** (OFX, CSV bancário, boleto, NFe, DANFE, NFC-e, holerite, recibo, cupom térmico, conta de luz/água): Protocolo Ouroboros processa, extrai granular, popula grafo, exporta nota `.md` com frontmatter para `Pessoal/Casal/Financeiro/Documentos/{YYYY-MM}/`.

3. **Preservação do original:** Ambos os motores **sempre copiam primeiro para local versionado do Ouroboros (`data/raw/originais/`)** antes de mover o arquivo na inbox. Zero perda de original.

4. **Grafo como cola:** Quando Ouroboros ingere documento, cria edges no grafo SQLite:
   - `documento → pago_com → transacao` (Sprint 48, incompleta — Sprint 74 completa)
   - `pessoa → documento_de → documento` (novo: ADR-20)
   - `documento → arquivo_original → {caminho_original_no_vault}` (novo)
   A nota `.md` gerada no vault tem frontmatter com `documento_id` e `transacao_id`, navegável via grafo Obsidian nativo.

5. **Workflow canônico** (vai para ADR-19):
   - `./run.sh` sem args → menu interativo
   - Opção `Processar Inbox` consome `~/Controle de Bordo/Inbox/`, roteia para motor apropriado, reporta resultado.
   - Ao fim: pergunta "Abrir dashboard? Gerar relatório? Ambos? Nada?"

6. **Configuração compartilhada:**
   - `~/Controle de Bordo/.sistema/config/devices.yaml` → identificação de autor/host
   - `mappings/contas_casal.yaml` (Sprint 68) continua no Ouroboros (whitelist de identidade bancária).
   - `.sistema/config/regras.yaml` pode ser lido pelo Ouroboros para estender categorização.
   - Ouroboros publica: `export/categorias.yaml`, `export/fornecedores.yaml` que o vault pode consumir via Dataview.

### Onde Ouroboros NÃO encosta

- `~/Controle de Bordo/Arquivo/` (NÃO sincroniza, pesado).
- `~/Controle de Bordo/.sistema/` exceto para ler config compartilhado (`devices.yaml`, `regras.yaml`).
- `~/Controle de Bordo/Trabalho/` (escopo do Andre profissional).
- `~/Controle de Bordo/Segredos/` (senhas/credenciais).

### Onde Ouroboros ESCREVE

- `~/Controle de Bordo/Pessoal/Casal/Financeiro/Documentos/{YYYY-MM}/{slug}.md` (nota por documento)
- `~/Controle de Bordo/Pessoal/Casal/Financeiro/Fornecedores/{slug}.md` (nota por fornecedor)
- `~/Controle de Bordo/Pessoal/Casal/Financeiro/Meses/{YYYY-MM}.md` (MOC mensal, já existe)
- `~/Controle de Bordo/Pessoal/Casal/Financeiro/Dashboard.md` (link para Streamlit + resumo)

## Alternativas consideradas

### A. Status quo (dois sistemas independentes)
- **Rejeitado:** usuário relata fricção de ter que pensar em dois lugares. Violação do princípio "central de tudo".

### B. Migrar Ouroboros inteiro para dentro do vault
- **Rejeitado:** código Python do Ouroboros não deve ser versionado pelo Obsidian sync; vault tem limite 1GB e dados financeiros já ocupam mais.

### C. Obsidian vault dentro do Ouroboros
- **Rejeitado:** vault é maior e mais antigo; migração seria dolorosa. Controle de Bordo já tem git próprio.

### D. ESCOLHIDA — Coabitação estrutural
Ouroboros permanece em `~/Desenvolvimento/protocolo-ouroboros/`, vault em `~/Controle de Bordo/`. Ouroboros CONSOME e ESCREVE via path absoluto configurável (`BORDO_DIR` env var, default `~/Controle de Bordo/`). Contrato formal de entrada e saída.

## Consequências

### Positivas
- Andre tem UMA inbox, uma forma de despejar documento.
- Zero duplicação de processador inteligente — cada motor faz sua parte, um fica fora do escopo do outro.
- Grafo Ouroboros vira backend factual do vault: toda nota em Pessoal/Casal/Financeiro tem fonte rastreável.
- Documentos antigos do vault (em `Pessoal/Documentos/`) podem ser indexados retroativamente pelo Ouroboros sem serem movidos.

### Negativas / custos
- Sprint 70 e 71 exigem modificar `run.sh`, criar adapter `src/integrations/controle_bordo.py`, testar com o vault real.
- Andre precisa aprovar o mapeamento explícito Pessoal/Casal/Financeiro (confirmar os subpaths propostos).
- Sincronização dupla (git do vault + git do Ouroboros) exige disciplina.

## Sprints desbloqueadas

- **Sprint 70** — Inbox unificada (Ouroboros lê de `~/Controle de Bordo/Inbox/`)
- **Sprint 71** — Sync rico bidirecional (vault ↔ Ouroboros)
- **Sprint 74** — Vinculação transação ↔ documento original (grafo + link vault)
- **Sprint 75** — Gap analysis (o que falta documentar)
- **Sprint 80** — `run.sh` interativo com menu

## Revisão

Andre precisa confirmar:
1. O mapeamento `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,Dashboard}.md` está OK? Ou prefere outro layout?
2. OK consumir `~/Controle de Bordo/Inbox/` diretamente, ou prefere mover para subfolder `Inbox/financeiro/`?
3. Aceita que documentos pessoais (RG, CV) fiquem FORA do escopo do Ouroboros por enquanto (só financeiro)?

---

*"Uma inbox só, uma central só, um fluxo só." — princípio da integração*
