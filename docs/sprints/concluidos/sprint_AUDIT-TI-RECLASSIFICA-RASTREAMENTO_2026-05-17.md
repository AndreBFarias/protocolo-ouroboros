---
id: AUDIT-TI-RECLASSIFICA-RASTREAMENTO
titulo: "Rastreamento granular de `_reclassificar_ti_orfas` (hoje só conta, não loga quais)"
status: concluída
concluida_em: 2026-05-17
prioridade: P1
data_criacao: 2026-05-17
fase: QUALIDADE
epico: 3
depende_de: []
esforco_estimado_horas: 1.5
origem: "auditoria independente 2026-05-17. `src/pipeline.py:383-440::_reclassificar_ti_orfas` degrada Transferência Interna (TI) para Despesa/Receita se descrição NÃO bate `e_transferencia_do_casal()` nem regex operacional. Log atual apenas conta N reclassificadas; sem lista, sem rastreabilidade, sem rollback se errar. Risco: transferência legítima para terceiro (filho, parceiro) degradada como Despesa permanente."
---

# Sprint AUDIT-TI-RECLASSIFICA-RASTREAMENTO

## Contexto

Pipeline tem estágio 6b (Sprint 68b) que reverte falsos-positivos de TI:

```python
def _reclassificar_ti_orfas(transacoes):
    n_revertidos = 0
    for t in transacoes:
        if t.get("tipo") != "Transferência Interna":
            continue
        if e_transferencia_do_casal(t):
            continue  # mantem TI
        if _bate_regex_operacional(t):
            continue  # mantem TI
        # Reverte para Despesa/Receita
        t["tipo"] = "Despesa" if t["valor"] < 0 else "Receita"
        n_revertidos += 1
    logger.info("Reclassificou %d TI orfãs", n_revertidos)
```

Problema: sem registro de QUAIS foram reclassificadas. Se 50 transações degradam e 2 eram legítimas, dono não tem como identificar quais.

## Hipótese e validação ANTES

```bash
grep -A 30 "_reclassificar_ti_orfas" src/pipeline.py | head -40
# Confirmar: só log de contagem
```

## Objetivo

1. **Marcar transações reclassificadas** com flag e razão:
   ```python
   t["_reclassificada_68b"] = True
   t["_razao_reclassificacao"] = "nao_bate_casal_nem_regex_operacional"
   t["_tipo_anterior"] = "Transferência Interna"
   ```

2. **Gravar log estruturado** `data/output/reclassificacao_ti_orfas_<ts>.json`:
   ```json
   {
     "executado_em": "ISO",
     "total_revertidas": 42,
     "amostras": [
       {
         "data": "2026-04-15",
         "valor": -1500.0,
         "local": "FULANO DA SILVA",
         "banco_origem": "Nubank",
         "razao": "nao_bate_casal_nem_regex_operacional"
       },
       ...
     ]
   }
   ```

3. **Dashboard nova aba ou KPI**: cluster Sistema mostra count de TI reclassificadas no último pipeline + link para JSON.

4. **Threshold de segurança opcional**: `_reclassificar_ti_orfas(margem=0.3)` — só reclassifica se score de "não é TI legítima" >= 0.3. Hoje implícito 0.0 (sempre reclassifica).

5. **Testes regressivos**:
   - `test_reclassifica_marca_flag_e_razao`
   - `test_reclassifica_grava_log_json`
   - `test_reclassifica_preserva_ti_casal`

## Não-objetivos

- Não desabilitar reclassificação (mantém função).
- Não tocar `e_transferencia_do_casal` ou regex operacional.
- Não tocar UI do dashboard (próxima sprint).

## Proof-of-work runtime-real

```bash
./run.sh --tudo
ls data/output/reclassificacao_ti_orfas_*.json | tail -1
.venv/bin/python -c "
import json, glob
p = sorted(glob.glob('data/output/reclassificacao_ti_orfas_*.json'))[-1]
d = json.load(open(p))
print(f'Reclassificadas: {d[\"total_revertidas\"]}')
print(f'Amostra: {d[\"amostras\"][0]}')
"
```

## Acceptance

- Flag `_reclassificada_68b=True` em transações afetadas.
- Log estruturado `data/output/reclassificacao_ti_orfas_<ts>.json` (gitignored).
- 3 testes regressivos verdes.
- Pytest baseline mantida.

## Padrões aplicáveis

- (e) PII never in INFO — JSON em data/output/ (gitignored).
- (l) Anti-débito — rastreabilidade preserva auditoria.
- (m) Branch reversível — `_tipo_anterior` permite rollback.

---

*"Reclassificação sem rastro é mutação silenciosa." — princípio da auditoria de fluxo*
