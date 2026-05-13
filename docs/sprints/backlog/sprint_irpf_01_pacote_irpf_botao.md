---
id: IRPF-01-PACOTE-IRPF-BOTAO
titulo: Sprint IRPF-01 -- Botão 'Gerar pacote IRPF <ano>' → ZIP completo on-demand
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint IRPF-01 -- Botão 'Gerar pacote IRPF <ano>' → ZIP completo on-demand

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 4
**Esforço estimado**: 5h
**Depende de**: MICRO-01
**Fecha itens da auditoria**: nenhum

## Problema

Pacote IRPF requer hoje compilar manualmente NFs, holerites, comprovantes, parcelamentos, DAS.

## Hipótese

Botão consulta grafo e empacota ZIP com: tabela XLSX (transações + fontes), pasta `nfs/`, pasta `holerites/`, pasta `das/`, pasta `medico/`, `relatorio.md` raiz com totais por categoria IRPF + dois banners de incompletude.

## Banners obrigatórios na v1 (decisão dono 2026-04-29)

V1 lança **incompleto por dois motivos conhecidos** -- não esconder do usuário. ZIP gerado deve conter os dois banners abaixo no `relatorio.md` raiz **E** como comentário inicial em `extrato_filtrado.csv`. Quando DOC-20 fechar e LINK-AUDIT-01 elevar cobertura, abrir IRPF-01b para enriquecer.

```
ATENÇÃO 1 -- Rendimentos de investimento ainda não cobertos.
Aguardando Sprint DOC-20 (extrator de extrato de corretora). Ações,
FIIs, RF, Tesouro Direto e cripto não aparecem neste pacote.

ATENÇÃO 2 -- Linking documento ↔ transação ainda parcial.
Auditoria 2026-04-29 mediu 13/6.086 transações com documento vinculado
no grafo (0,21%). Sprints LINK-AUDIT-01 e LINK-TUNING-01 estão em curso
para subir essa cobertura. Documentos não vinculados ainda aparecem
no ZIP (pasta nfs/, holerites/, das/, medico/) mas correlação 1-a-1
com transação no extrato pode ser incompleta.
```

## Princípio operacional reforçado pelo dono em 2026-04-29

> "A ideia é extrair tudo das imagens e pdfs, tudo mesmo, cada valor e catalogar tudo. Tudo."

Aplicação ao IRPF-01: o ZIP deve incluir **todos os documentos de cada categoria fiscal**, mesmo aqueles sem `documento_de` ainda mapeada. Pasta `nfs/` carrega NFs ingeridas; pasta `holerites/` carrega 24 holerites (não só os 20 vinculados); pasta `das/` carrega 19 DAS PARCSN (não só os 5 vinculados). Linking parcial aparece como nota no relatorio.md, não como filtro de inclusão.

## Implementação proposta

`src/analysis/pacote_irpf.py` consumindo grafo + `irpf_tagger.py` existente + 164 arestas `irpf` + 4 nodes `tag_irpf`. UI: botão dashboard "Gerar pacote IRPF \<ano\>" com seletor de ano e barra de progresso. Output em `data/output/pacote_irpf_<ano>.zip`.

## Proof-of-work (runtime real)

Gerar pacote 2025 → ZIP com:
- 100% dos holerites do ano (mesmo sem `documento_de`).
- 100% dos DAS PARCSN do ano (mesmo sem `documento_de`).
- 100% das NFs ingeridas do ano (mesmo sem `documento_de`).
- 100% das receitas médicas + exames ingeridos do ano (mesmo sem `documento_de`).
- 100% das transações classificadas como dedutíveis via `irpf_tagger`.
- `relatorio.md` com 2 banners de incompletude no topo.
- `extrato_filtrado.csv` com comentário inicial reproduzindo os 2 banners.

## Acceptance criteria

- Botão funcional no dashboard.
- ZIP estruturado conforme acima.
- 2 banners obrigatórios visíveis em `relatorio.md` E `extrato_filtrado.csv`.
- Cobertura total: cada documento ingerido do ano aparece na pasta correspondente, sem filtro por linking.
- ≥6 testes (geração de ZIP, presença de banners, cobertura total).

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` exit 0 quando aplicável (>=3 amostras 4-way).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
