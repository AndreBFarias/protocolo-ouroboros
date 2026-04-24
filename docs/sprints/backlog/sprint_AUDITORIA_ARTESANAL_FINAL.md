## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDITORIA-ARTESANAL-FINAL
  title: "Auditoria artesanal final -- mover tudo para inbox + revisar cada classificação/extração com o usuário"
  touches:
    - path: inbox/
      reason: "receber todos os arquivos de data/raw/ de volta"
    - path: data/raw/
      reason: "esvaziar temporariamente (preservar data/raw/originais/ + data/raw/_envelopes/)"
    - path: docs/auditoria_artesanal_2026-XX-XX.md
      reason: "relatório vivo: 1 seção por arquivo revisado pelo usuário"
  forbidden:
    - "Executar sem supervisão humana (sprint é por definição interativa)"
    - "Perder data/raw/originais/ (preservação hash-based inviolável ADR-18)"
    - "Deletar arquivos do vault Controle de Bordo"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Script scripts/reset_para_inbox.py move todos os PDFs/CSVs/JPEGs de data/raw/<pessoa>/<banco>/ de volta para inbox/ preservando data/raw/originais/ e data/raw/_envelopes/"
    - "Após reprocessamento completo (--tudo), cada arquivo teve classificação revisada 1-a-1 com o usuário"
    - "Relatório vivo em docs/auditoria_artesanal_2026-XX-XX.md documenta: arquivo, tipo detectado, pessoa detectada, extração ok/falha, decisão do usuário, ajustes YAML/código aplicados"
    - "Baseline de testes mantida ou ampliada"
    - "Zero regressões no smoke aritmético"
  proof_of_work_esperado: |
    # Antes
    ls inbox/
    # = vazio (após fase 3 do conserta-tudo)

    # Rota
    .venv/bin/python scripts/reset_para_inbox.py --dry-run
    .venv/bin/python scripts/reset_para_inbox.py --executar
    ls inbox/ | wc -l  # ~760 arquivos

    # Reprocessamento + revisão interativa
    ./run.sh --tudo
    # Para cada pasta sob data/raw/, usuário e IA revisam em sessão

    # Depois
    # - docs/auditoria_artesanal_<data>.md com cada arquivo anotado
    # - ajustes em mappings/ conforme necessário
    # - possíveis sprint-filhas para fixes estruturais descobertos
```

---

# Sprint AUDITORIA-ARTESANAL-FINAL -- Revisão 1-a-1 de cada classificação/extração

**Status:** BACKLOG (última da rota "conserta tudo")
**Prioridade:** P0 ao chegar nela -- é a validação terminal da saúde do pipeline
**Dependências:** Todas as outras sprints da rota "conserta tudo" (P0.1, P0.2, P1.1, P1.2, P2.1, P2.2, P2.3, P3.1, P3.2) e fases pós-crash seguintes (ressalvas, ZETA, backlog formal)
**Origem:** pedido do dono 2026-04-23 -- "ao final movermos tudo de volta pra inbox e ir avaliando cada classificação de cada/extração e afins"

## Motivação

Depois de todos os fixes da rota "conserta tudo" + Fase ZETA + backlog formal, o pipeline está funcionando corretamente em teoria (gauntlet verde, contratos aritméticos OK, grafo populado). Mas teoria não é prática.

Esta sprint é a validação terminal: mover tudo de volta para inbox, reprocessar com o sistema melhorado, e revisar artesanalmente cada decisão de classificação/extração em sessão interativa com o dono.

É a contraparte canônica da auditoria 2026-04-23 que originou a rota "conserta tudo" -- agora **com o sistema corrigido**, rodando de volta em corpus real, validando que cada fix funcionou em volume.

## Escopo

### Fase 1 -- Preparação

1. Script `scripts/reset_para_inbox.py` que:
   - Lista todos os arquivos em `data/raw/<pessoa>/<banco>/...` (não-recursivo nas pastas `_envelopes/`, `_conferir/`, `originais/`).
   - Move cada arquivo de volta para `inbox/`.
   - Preserva integralmente `data/raw/originais/`, `data/raw/_envelopes/`, `data/raw/_conferir/`, `data/raw/_classificar/`.
   - Default: `--dry-run`. Requer `--executar` explícito.
   - Gera log do que foi movido (~760 arquivos esperados).

2. Backup de segurança: `data/output/grafo.sqlite` e `data/output/ouroboros_*.xlsx` copiados para `data/output/backup_pre_artesanal/` antes da rota.

### Fase 2 -- Reprocessamento

1. `./run.sh --inbox` processa todos os ~760 arquivos (classifier + router).
2. `./run.sh --tudo` roda pipeline completo (extratores + grafo + XLSX).
3. Registrar contagens pós-reprocessamento: nodes, edges, documentos, aba renda, smoke aritmético.

### Fase 3 -- Revisão artesanal interativa

Sessão interativa estruturada (dono + IA):

Para cada pasta em `data/raw/<pessoa>/<banco>/`, listar os arquivos e para **cada arquivo**:

- Abrir e inspecionar conteúdo original.
- Confirmar classificação (pessoa, banco, tipo de documento).
- Confirmar extração (transações no XLSX, documento no grafo, dados parseados).
- Registrar no relatório vivo: ok / ressalva / bug.

Relatório vivo: `docs/auditoria_artesanal_<data>.md` com seções por pasta e linha por arquivo.

### Fase 4 -- Fechamento

- Consolidar achados em lista priorizada.
- Sprint-filhas para correções não-triviais.
- Move sprint para `docs/sprints/concluidos/`.

## Armadilhas

- **Volume enorme:** ~760 arquivos inviabiliza revisão 1-a-1 literal. Rota realista: revisão **por pasta** (28 subpastas), amostragem de 3-5 arquivos-âncora cada, seguindo padrão da auditoria 2026-04-23. Escopo ajustável conforme disponibilidade do dono.
- **Reprocessamento caro:** `./run.sh --tudo` em 760 arquivos pode demorar minutos. OCR de cupons fotografados + tesseract em NFCe-imagem são os gargalos. Não é bloqueio, só planejamento.
- **Idempotência depende de P2.3:** o dedupe de roteamento por hash (Sprint P2.3) é pré-requisito para que reprocessamento não gere duplicatas `_1.pdf`, `_2.pdf`.
- **Preservar originais é inviolável:** `data/raw/originais/` nunca pode ser deletado (ADR-18). Confirmar no dry-run.

## Sub-sprints possíveis descobertas durante a revisão

Este documento servirá como gerador de sprints-filhas. Exemplos esperados:
- Ajustes em `mappings/fontes_renda.yaml` (descobrir MEIs não-listados).
- Refinamentos em `mappings/pessoas.yaml` (aliases que pegam errado).
- Bugs estruturais em extratores descobertos em volume.
- Documentos não-classificáveis que precisam de extrator novo.

---

*"A única auditoria que vale é aquela onde se olha o arquivo com os próprios olhos." -- princípio do validador minucioso*
