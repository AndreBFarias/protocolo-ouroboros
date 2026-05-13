---
id: INFRA-LINKING-DIRPF-TOTAL-ZERO
titulo: DIRPF com total=0.0 entra no linking heurístico por valor e casa transações aleatórias
status: concluída
concluida_em: 2026-05-13
prioridade: P1
data_criacao: 2026-05-13
fase: SANEAMENTO
depende_de: []
esforco_estimado_horas: 2
origem: auditoria pós-./run.sh --tudo em 2026-05-13 -- 3 propostas conflito (007462, 007583, 007768) todas para DIRPF|05127373122|2025_RETIF com total=0.0 e candidatas casadas via diff_valor=0.01.
---

# Sprint INFRA-LINKING-DIRPF-TOTAL-ZERO

## Contexto

Pipeline `./run.sh --tudo` (HEAD c3aca7b, executado 2026-05-13 00:30) gerou 21 conflitos de linking. Padrão identificado:

- Documento `DIRPF|05127373122|2025_RETIF` (id grafo 7768) tem `total: 0.0`.
- Heurística `data_valor_aproximado` casa-o contra 3 transações (rank 1-3) com `diff_valor: 0.01` e `diff_dias: -20/-45/-48`.
- Como o total é zero, qualquer transação pequena (R$ 0.01) bate proporcionalmente.

Conflitos identificados: 3 propostas distintas (007462, 007583, 007768) — provavelmente 3 versões da mesma DIRPF acumuladas no grafo. Antes de filtrar, conferir se são retificações legítimas ou lixo.

## Objetivo

Filtrar documentos com `total <= 0.01` ou `total IS NULL` ANTES de aplicar heurística `data_valor_aproximado`. DIRPF e similares geralmente não têm total monetário direto (retificadora pode até ter restituição a receber, mas o ARQUIVO em si não tem total movimento).

## Proof-of-work esperado

```bash
.venv/bin/python -c "
from src.graph.linking import linking_documento_transacao
result = linking_documento_transacao(dry_run=True)
assert result['conflitos'] < 21, f'Conflitos pós-fix: {result[\"conflitos\"]} (era 21)'
print(f'DIRPF conflitos: {result.get(\"dirpf_filtrados\", \"sem flag\")}')
"
```

## Padrão canônico aplicável

(s) Validação ANTES, (gg) Cache sintético/dado vazio não pode virar gabarito.

---

*"Linkar dado vazio é ato de fé; ato de fé não reduz incerteza." -- princípio anti-magia do arquivista*

---

## Conclusão (2026-05-13)

Filtro implementado em `src/graph/linking.py` em três camadas (padrão `(n)` defesa em camadas):

1. Constante `TOTAL_MINIMO_ELEGIVEL = 0.01` (linhas ~57-68 do módulo).
2. Helper puro `_total_vazio_ou_minimo(total)` que classifica `None`, não-numérico,
   zero ou módulo abaixo do limite como inelegível.
3. `candidatas_para_documento` retorna `[]` cedo quando o filtro casa (linhas ~283-294).
4. `linkar_documentos_a_transacoes` pula antes de qualquer consulta a candidatas e
   contabiliza o documento em `stats["total_vazio"]` com log INFO sem PII além do
   `nome_canonico` já presente (linhas ~393-419).

### Linhas tocadas

- `src/graph/linking.py`: +49 linhas (constante + helper + dois filtros + comentários).
- `tests/test_linking_filtro_total_zero.py`: novo arquivo com 16 testes (helper, candidatas, orquestrador).

### Métricas

- Pytest novo arquivo: 16/16 passou.
- Pytest módulos linking existentes (`test_linking*.py`): 48/48 passou — zero regressão.
- `make lint`: exit 0 (ruff + check_acentuacao + check_cobertura_total).
- `make smoke`: 10/10 contratos OK.

### Proof-of-work runtime real

```python
.venv/bin/python -c "
from pathlib import Path
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.linking import linkar_documentos_a_transacoes
destino = Path('/tmp/propostas_pos_fix')
with GrafoDB(caminho_padrao()) as db:
    stats = linkar_documentos_a_transacoes(db, caminho_propostas=destino)
print(stats)
"
```

Saída literal:

```
linking concluído: {'linkados': 25, 'conflitos': 20, 'baixa_confianca': 0,
                    'sem_candidato': 5, 'ja_linkados': 0, 'total_vazio': 1}
documento DIRPF|05127373122|2025_RETIF (dirpf_retif) com total ausente/<=0.01
  -- fora do linking por valor
```

- DIRPF retif com `total=0.0` agora cai no contador `total_vazio` (1 documento).
- Zero arquivos de proposta DIRPF gerados no destino (`grep -c dirpf` = 0).
- Estado original em `docs/propostas/linking/`: 3 propostas DIRPF retif (007462, 007583, 007768)
  sobreviveram apenas como artefato antigo; o pipeline corrente não as recria.

### Padrões canônicos aplicados

- `(k)` Hipótese empírica verificada por grep antes de codar — confirmadas as 3 propostas
  DIRPF em `docs/propostas/linking/` com `total: 0.0` no frontmatter.
- `(n)` Defesa em camadas: helper + filtro em `candidatas_para_documento` + filtro em
  `linkar_documentos_a_transacoes`.
- `(o)` Subregra retrocompatível: `stats` ganha chave nova `total_vazio` sem remover/renomear
  as cinco originais. Consumidores antigos seguem funcionando.
- `(s)` Validação ANTES: grep das funções alvo + leitura dos arquivos de proposta.
- `(u)` Proof-of-work runtime real: comando contra o grafo de produção (`caminho_padrao()`).
- `(gg)` Cache/dado vazio não vira gabarito: documento com `total=0.0` declara "sem valor
  monetário direto" e o linker respeita essa semântica em vez de inferir match por proporção.

### Não-objetivos (deixados explicitamente para depois)

- Limpeza das 3 propostas DIRPF retif antigas (`007462`, `007583`, `007768`) já gravadas em
  `docs/propostas/linking/` — quem decide se vira sprint de saneamento de propostas órfãs
  ou se a próxima rodada `./run.sh --tudo` sobrescreve. Não é responsabilidade desta sprint.
- Investigação se há 3 versões reais da mesma DIRPF retificadora no grafo (provável duplicação
  por ingestão repetida). Caso confirmado, vira sprint-filha de dedup de documentos.
- Revisar limite `TOTAL_MINIMO_ELEGIVEL = 0.01` para outros tipos (certidão, contrato sem
  valor). Por ora o limite é global; caso surja documento legítimo com R$ 0,01 (improvável),
  promover a parâmetro por tipo em `linking_config.yaml`.

### Achados colaterais

Nenhum bloqueio adicional encontrado no caminho. As 6 falhas de pytest da baseline
(`test_mobile_cache_bem_estar`, `test_normalizar_path_relativo`) já existiam antes do fix
e não tocam o motor de linking — fora do escopo desta sprint.

### Commit

`feat(INFRA-LINKING-DIRPF-TOTAL-ZERO): filtra documentos com total ausente ou <= R$ 0,01 do funil heurístico de linking`

