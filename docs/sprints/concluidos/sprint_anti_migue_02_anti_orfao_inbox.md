# Sprint ANTI-MIGUE-02 -- Anti-órfão na inbox

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29, item 30, P0).
**Prioridade**: P0
**Onda**: 1
**concluida_em**: 2026-04-29
**Esforço real**: 3h
**Commit**: `743158d`

## Problema

P0 da auditoria honesta: arquivo entra em `data/raw/_classificar/` ou `data/raw/_conferir/` e **nunca produz node `documento` no grafo**. Sem alerta, sem relatório, sem sprint formal disparada — perda silenciosa de dados.

Mecanismo de linking existia (`src/graph/linking.py` com 26 referências a `documento_de`), mas zero monitoração de "arquivo na inbox há > 24h sem integração".

## Hipótese

Módulo dedicado `src/intake/anti_orfao.py` que:
1. Varre por padrão a **zona de estagiário** (`_classificar/` + `_conferir/`) — onde a perda silenciosa acontece. Modo `--abrangente` opcional varre `data/raw/` inteiro.
2. Indexa nodes `documento` no grafo por `metadata.arquivo_origem`.
3. Classifica cada arquivo em 4 estados: `integrado`, `catalogado_orfao`, `orfao_total` (recente <24h), `orfao_total_antigo` (>24h, alerta).
4. Gera relatório Markdown `data/output/orfaos.md`.
5. Modo `--strict` retorna exit 1 se há órfãos antigos (futuro: bloqueia merge em PR).

## Implementação

- `src/intake/anti_orfao.py` (250 linhas) com 4 funções públicas: `varrer_arquivos_inbox`, `mapear_documentos_no_grafo`, `classificar`, `gerar_relatorio` + `main`.
- Encadeado em `./run.sh --full-cycle` (passo final, falha-soft).
- Encadeado em `./run.sh --reextrair-tudo` (após backfill_razao_social).
- 8 testes regressivos cobrindo varredura padrão/abrangente, mapeamento, classificação 4-estado, geração de relatório, modo strict, modo observador.

## Proof-of-work runtime real

```
$ python -m src.intake.anti_orfao
[ANTI-ORFAO] 0 integrados | 0 catalogados órfãos | 2 órfãos recentes |
              1 órfãos antigos (>24h) | relatório: data/output/orfaos.md
```

Achado real: **1 órfão antigo** (`_CLASSIFICAR_6c1cc203.pdf` — resíduo da Sprint 106a, cupom-foto detectado como ilegível) + **2 cupons** em `_conferir/` aguardando confirmação humana. Antes desta sprint, esses arquivos estavam invisíveis ao operador.

## Acceptance atendido

- [x] Módulo criado com 4 funções públicas + main CLI.
- [x] Relatório `data/output/orfaos.md` em runtime real.
- [x] Encadeado em `--full-cycle` e `--reextrair-tudo`.
- [x] 8 testes regressivos (pytest baseline 2.019 → 2.027).
- [x] Modo `--strict` retorna exit 1 quando há órfãos antigos.
- [x] Modo `--abrangente` opcional para auditoria geral.
- [x] Lint exit 0, smoke 10/10.

## Limitação conhecida (sprint-filha já criada)

O critério atual usa apenas presença de node `documento` + aresta `documento_de`. Arquivos cujo conteúdo gera transações diretas (extratos bancários, OFX) não criam node `documento` — ficam de fora da varredura padrão (que se restringe à zona de estagiário). Modo `--abrangente` mostra essa categoria como "órfão total", o que pode confundir.

Sprint-filha futura (não-bloqueante): rastreabilidade arquivo→transação no grafo (edge tipo `extraido_de` apontando do node `transacao` para um node `arquivo`). Hoje a aresta `origem` aponta para `conta`, não para arquivo.
