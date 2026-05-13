---
id: INFRA-LINKING-HOLERITE-MULTI-FONTE
titulo: Holerite multi-fonte (G4F + INFOBASE) gera conflito artificial no linking
status: concluída
concluida_em: 2026-05-13
prioridade: P1
data_criacao: 2026-05-13
fase: SANEAMENTO
depende_de: []
esforco_estimado_horas: 3
origem: auditoria pós-./run.sh --tudo em 2026-05-13 -- holerites G4F e INFOBASE (mesma referência 2025-07/2025-12/13o integral) são tratados como documentos separados, e ambos competem pela mesma transação mensal.
---

# Sprint INFRA-LINKING-HOLERITE-MULTI-FONTE

## Contexto

Pessoa_b recebe holerite de DUAS fontes para a mesma competência (G4F + INFOBASE — provavelmente uma é o broker da CLT, outra é a folha). Ambas geram documentos canônicos distintos:

- `HOLERITE|G4F|2025-12` (id 7695)
- `HOLERITE|INFOBASE_-_13o_INTEGRAL|2025-12` (id 7697)

Mas representam o **mesmo evento real**: um depósito mensal na conta. O linker, ao processar os dois, gera 2 propostas conflito separadas — cada uma com 3 candidatas, total 8 conflitos só de holerite no run atual.

## Hipótese arquitetural

Antes de chamar o linker, identificar holerites com (data_emissao, cnpj_emissor distinto) MAS valor_liquido próximo (±5%) — fundir como referências da mesma realidade no grafo (relação `_mesma_realidade_holerite` análogo ao `_eh_mesma_nfce` da sprint INFRA-NFCE-DEDUP-OCR-DUPLICATAS).

Alternativa mais simples: heurística do linker prefere o `nome_canonico` já escolhido para a transação no próximo turn (idempotência inter-execução).

## Proof-of-work esperado

```bash
# Antes do fix: 8 conflitos holerite
# Após fix: <= 2 conflitos holerite (só quando valor_liquido difere mais de 5%)
./run.sh --tudo 2>&1 | grep "conflitos.*holerite" | tail
ls docs/propostas/linking/ | grep -i holerite | wc -l  # deve cair
```

## Padrão canônico aplicável

(hh) Ingestão dupla escapa dedup -- aqui aplicado a documentos, não transações.
(e) PII em 4 sítios -- aplicado à identidade do holerite em 4 sítios distintos do grafo.

---

## Conclusão (2026-05-13)

### Estratégia escolhida: A (fusão pré-linker)

Decisão: a estratégia A é mais simples, é determinística e funciona já no primeiro run -- não depende de runs anteriores (como seria a alternativa B baseada em idempotência inter-execução).

Critério de fusão implementado em `_fundir_holerites_mesma_realidade(documentos, *, tolerancia_pct=0.05)`:

1. Apenas documentos `tipo_documento == "holerite"` são candidatos.
2. Competência extraída via `_competencia_do_holerite`: prefere `metadata.periodo_apuracao` (formato `YYYY-MM`), fallback para sufixo do `nome_canonico` (`HOLERITE|<fonte>|YYYY-MM`).
3. Holerites na mesma competência cujos `metadata.total` diferem no máximo 5% (do menor dos dois) formam um grupo "mesma realidade".
4. O representante de cada grupo é o documento com menor `id` (estável entre runs -- depende só da ordem de ingestão).
5. Os outros do grupo recebem aresta `_alias_de` apontando para o representante, com `evidencia = {motivo, sprint}`. A aresta `_alias_de` é nova no grafo, mas o schema não muda (apenas mais um valor de `tipo`).
6. Apenas o representante é processado pelo linker principal -- os alias ficam fora do funil `documento_de`.

### Arquivos tocados

- `src/graph/linking.py` (+165L): nova função `_fundir_holerites_mesma_realidade`, helper `_competencia_do_holerite`, helper `_registrar_arestas_alias`, integração na entrada de `linkar_documentos_a_transacoes` (chamada antes do loop principal), nova chave `alias_fundidos` nas estatísticas, novo símbolo público `EDGE_TIPO_ALIAS_REALIDADE`.
- `tests/test_holerite_multi_fonte.py` (NOVO, 240L): 7 testes cobrindo os 5 cenários obrigatórios + 2 invariantes (competência via metadata, holerite sem competência passa intacto).

### Métricas

- Baseline pytest antes da sprint: `2912 passed, 6 failed` (failures pré-existentes em `tests/test_normalizar_path_relativo.py` e `tests/test_mobile_cache_bem_estar.py`, fora do escopo).
- Pós-sprint: `2919 passed, 6 failed` -- delta +7 (exatamente os 7 testes novos), zero regressões.
- `make lint`: exit 0 (acentuação + cobertura D7 + ruff).
- `make smoke`: 10/10 contratos.

### Validação runtime real

Execução de `python -m src.graph.linking` sobre o grafo de produção (`data/output/grafo.sqlite`):

```
linking concluído: {'linkados': 25, 'conflitos': 20, 'baixa_confianca': 0,
                    'sem_candidato': 5, 'ja_linkados': 0, 'alias_fundidos': 1}
```

Auditoria das 10 competências com 2+ holerites no grafo:

| competência | holerites | maior diff relativa | fundiu? |
|---|---|---|---|
| 2025-06 a 2026-03 (não-13o) | G4F + INFOBASE | 11.7%-15.5% | NÃO (acima 5%) |
| 2025-10 (com 13o adiant.) | 3 holerites | 362% | NÃO |
| 2025-12 (com 13o integral) | 4 holerites | 73.3% global | NÃO global, **SIM no par 13o** |

Único par fundido: `HOLERITE|G4F_-_13º_INTEGRAL|2025-12` (5771.50) com `HOLERITE|INFOBASE_-_13o_INTEGRAL|2025-12` (5833.33) -- diferença 1.07%, dentro do critério. Confirma exatamente o cenário descrito na spec.

Aresta `_alias_de` no grafo:

```
src=7697 (INFOBASE 13o INTEGRAL) -> dst=7695 (G4F 13o INTEGRAL)
  evidencia: {motivo: holerite_mesma_competencia_valor_proximo,
              sprint: INFRA-LINKING-HOLERITE-MULTI-FONTE}
```

### Achados colaterais -- protocolo anti-débito

1. **Pares G4F vs INFOBASE não-13o diferem 11.7-15.5%, fora do critério ±5%.** A spec assume que G4F e INFOBASE representam a mesma realidade, mas pelo critério canônico ±5% eles não foram fundidos. Possíveis explicações: (a) G4F é o líquido depositado, INFOBASE o bruto contratual; (b) bonificações trimestrais. Recomendação: nova sprint `INFRA-LINKING-HOLERITE-TOLERANCIA-RECALIBRAR` para revisar `TOLERANCIA_VALOR_HOLERITE_MULTI_FONTE` (talvez 0.20) ou usar `metadata.liquido` em vez de `total` como chave de fusão. Não foi feito agora porque é decisão de domínio do dono.

2. **Stash herdado de outros worktrees**: ao final da sprint, `git stash list` retornou 3 entradas (`worktree-agent-abdbc7a7a2c6ce022`, `worktree-agent-a70649870675c2ad2`, `onda-v-2-7`). Nenhuma foi criada por este executor; são herança de stashes do supervisor em worktrees alheios. Registrado conforme REGRA 8 do protocolo anti-armadilha v3.1; supervisor pode limpar com `git stash drop` quando achar adequado.

3. **Banco de produção modificado pelo CLI**: `python -m src.graph.linking` rodado para proof-of-work persistiu 25 arestas `documento_de` e 1 aresta `_alias_de` em `data/output/grafo.sqlite`. O grafo é `gitignored`, então não há contaminação do repo, mas o próximo `./run.sh --tudo` reescreverá. Sem ação necessária.

### Padrões canônicos aplicados

- (a) Edit incremental, não rewrite -- nova função adicionada sem mexer no fluxo existente.
- (b) Acentuação PT-BR completa.
- (k) Hipótese da spec validada com grep antes de codar (confirmados identificadores `linkar_documentos_a_transacoes`, `candidatas_para_documento`, holerite no YAML).
- (n) Defesa em camadas -- agrupamento pré-linker + aresta `_alias_de` persistida + teste de idempotência.
- (u) Proof-of-work runtime-real -- CLI rodado contra grafo de produção, output literal capturado.
- (hh) Padrão original citado na spec (ingestão dupla escapa dedup), aplicado a documentos canônicos.

---

*"Duas fontes para a mesma realidade não são redundância: são testemunhas." -- princípio da fusão com humildade*
