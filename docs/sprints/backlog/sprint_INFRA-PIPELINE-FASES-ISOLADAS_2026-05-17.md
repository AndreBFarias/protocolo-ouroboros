---
id: INFRA-PIPELINE-FASES-ISOLADAS
titulo: "Split `_executar_corpo_pipeline` (156L) em fases isoladas com stats"
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-17
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 3
origem: "auditoria independente 2026-05-17. `src/pipeline.py:919-1075` (156L) orquestra 16 estágios sequenciais mutando lista `transacoes` in-place. Difícil testar fase isolada. Risco: estágio falha parcialmente sem rastreabilidade (ex: `_reclassificar_ti_orfas` reclassifica N transações com log de contagem mas sem lista de afetadas). Padrão `(p)` validação fina exige saber QUAIS itens passaram em CADA fase."
---

# Sprint INFRA-PIPELINE-FASES-ISOLADAS

## Contexto

Após `_executar_backup_grafo()`, o corpo do pipeline executa em sequência:

1. `_descobrir_extratores` → classes
2. `_escanear_arquivos` → arquivos
3. `_extrair_tudo` → transações brutas
4. `_importar_historico` → +histórico
5. `deduplicar` → -duplicatas
6. `Categorizer.categorizar_lote` → +categoria
7. `_reclassificar_ti_orfas` → reverte TI duvidosa
8. `aplicar_tags_irpf` → +tags
9. `gerar_xlsx` → escrita
10. `gerar_relatorios` → markdowns
11. (...mais 5 estágios)

Cada um muta `transacoes` in-place. Falha parcial no estágio 7 deixa estado misto (categorias OK, sem tags IRPF). Não há rollback granular.

**Sprint INFRA-PIPELINE-TRANSACIONALIDADE** (concluída) adicionou `GrafoDB.transaction()` mas só para SQLite. O pipeline em memória ainda é monolítico.

## Hipótese e validação ANTES

```bash
wc -l src/pipeline.py
awk '/^def _executar_corpo_pipeline/,/^def /' src/pipeline.py | wc -l
# Esperado: ~156 linhas
```

## Objetivo

1. Extrair cada fase em função pura `(transacoes, ctx) -> (transacoes_novas, stats)`:
   ```python
   def fase_extrair(arquivos, classes, ctx) -> tuple[list, dict]:
       transacoes = _extrair_tudo(arquivos, classes)
       stats = {"n_extraidas": len(transacoes), "por_extrator": ...}
       return transacoes, stats

   def fase_categorizar(transacoes, ctx) -> tuple[list, dict]:
       cat = Categorizer()
       resultado = cat.categorizar_lote(transacoes)
       stats = {"n_categorizadas": ..., "outros_pct": ...}
       return resultado, stats
   ```

2. `_executar_corpo_pipeline` vira orquestrador linear de chamadas:
   ```python
   def _executar_corpo_pipeline(mes, processar_tudo):
       ctx = {"mes": mes, "tudo": processar_tudo}
       resultados = []
       for nome_fase, fn in FASES:
           _ESTAGIO_ATUAL = nome_fase
           inicio = time.monotonic()
           transacoes, stats = fn(transacoes, ctx)
           stats["duracao_s"] = time.monotonic() - inicio
           resultados.append((nome_fase, stats))
       _gravar_log_fases(resultados)
   ```

3. Log estruturado `data/output/pipeline_fases_<ts>.json` com stats por fase (n_in, n_out, duração, erros).

4. Testes regressivos por fase (sem rodar pipeline inteiro).

## Não-objetivos

- Não alterar lógica de cada estágio (apenas extrair em função).
- Não paralelizar (manter sequencial — ordem importa).
- Não tocar backup/restore (já transacional).

## Proof-of-work runtime-real

```bash
.venv/bin/python -c "
from src.pipeline import fase_categorizar
t = [{'local': 'X', 'valor': -100}]
res, stats = fase_categorizar(t, {})
print(stats)
"
# Esperado: dict com n_categorizadas, etc

./run.sh --tudo
cat data/output/pipeline_fases_*.json | head -5
# Esperado: log com 16 entries (uma por fase)
```

## Acceptance

- `_executar_corpo_pipeline` < 60L.
- 16 funções de fase isoladas e testáveis individualmente.
- Log `pipeline_fases_<ts>.json` gerado a cada execução.
- 5+ testes regressivos por fase (cobertura crescida).
- Pytest baseline mantida.

## Padrões aplicáveis

- (a) Edit cirúrgico — preserva semântica.
- (n) Defesa em camadas — falha em fase não afeta outras.
- (kk) Sprint encerra com produto final — log granular pronto.

---

*"Função grande esconde bugs; função pequena os denuncia." — princípio do split"*
