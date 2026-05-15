---
id: FIX-REGREDINDO-SEMANTICA
titulo: Corrigir semântica do campo `amostras_divergentes` e transição REGREDINDO
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-15
fase: PRODUCAO_READY
epico: 1
depende_de: []
esforco_estimado_horas: 2
origem: auditoria 2026-05-15. `scripts/dossie_tipo.py::cmd_graduar_se_pronto` linhas 491-494 testam `status_antes == STATUS_GRADUADO` antes de marcar REGREDINDO. Na primeira graduação `status_antes` é PENDENTE → nunca dispara. Em graduações posteriores, dispara FALSAMENTE porque `amostras_divergentes` acumula histórico (nunca esvazia ao revalidar OK). Caso vivo em `data/output/dossies/cupom_fiscal_foto/estado.json`: 3 hashes em `amostras_ok` E os mesmos 3 hashes em `amostras_divergentes`.
---

# Sprint FIX-REGREDINDO-SEMANTICA

## Contexto

A função `cmd_graduar_se_pronto` é o gate canônico do ciclo de graduação. Ela decide se um tipo merece transição entre PENDENTE → CALIBRANDO → GRADUADO → REGREDINDO. O ramo REGREDINDO existe no código mas nunca dispara corretamente.

`amostras_divergentes` foi pensado como "amostras que divergem agora" mas o código só ADICIONA hashes e nunca REMOVE — vira histórico cumulativo, não estado atual.

## Hipótese e validação ANTES (padrão (k))

H1: Nenhum tipo está em REGREDINDO hoje (counter=0 em `graduacao_tipos.json`), embora `cupom_fiscal_foto` tenha 3 divergentes históricas resolvidas.

```bash
cat data/output/dossies/cupom_fiscal_foto/estado.json | python -c "
import json, sys
d = json.load(sys.stdin)
print('status:', d['status'])
print('amostras_ok:', len(d['amostras_ok']))
print('amostras_divergentes:', len(d['amostras_divergentes']))
print('intersecao:', len(set(d['amostras_ok']) & set(d['amostras_divergentes'])))
"
# Esperado: status=GRADUADO, ok=3, divergentes=3, intersecao=3
```

## Objetivo

1. Renomear `amostras_divergentes` → `_historico_divergencias` (acumula sempre).
2. Criar campo novo `divergencias_ativas` (esvazia ao revalidar OK).
3. Atualizar `_marcar_amostra_ok` para remover de `divergencias_ativas`.
4. `cmd_graduar_se_pronto` testa `divergencias_ativas` (não histórico) para REGREDINDO.
5. Remover condição `status_antes == STATUS_GRADUADO` — REGREDINDO deve disparar mesmo na primeira tentativa se há divergência ativa.
6. Migrador idempotente que atualiza schema dos 10 dossiês existentes (`amostras_divergentes` → split entre os 2 novos campos).

## Não-objetivos

- Não renomear `amostras_ok` (continua significando "verdes atualmente").
- Não tocar lógica de PENDENTE → CALIBRANDO (estável).
- Não alterar o dashboard nesta sprint (UX-DASH-GRADUACAO-TIPOS endereça).

## Proof-of-work runtime-real

```bash
# 1. Backfill dos 10 dossies existentes
.venv/bin/python scripts/dossie_tipo.py snapshot

# 2. cupom_fiscal_foto deve estar GRADUADO com divergencias_ativas=[]
.venv/bin/python -c "
import json
e = json.load(open('data/output/dossies/cupom_fiscal_foto/estado.json'))
assert e['status'] == 'GRADUADO'
assert len(e['divergencias_ativas']) == 0
assert len(e['_historico_divergencias']) == 3
print('OK semantica corrigida')
"

# 3. Forçar REGREDINDO sintético
.venv/bin/python -c "
from scripts.dossie_tipo import _ler_estado, _gravar_estado, cmd_graduar_se_pronto
e = _ler_estado('cupom_fiscal_foto')
e['divergencias_ativas'] = ['HASH_FAKE_DIVERGENTE']
_gravar_estado('cupom_fiscal_foto', e)
cmd_graduar_se_pronto('cupom_fiscal_foto')
e = _ler_estado('cupom_fiscal_foto')
assert e['status'] == 'REGREDINDO'
print('OK detector REGREDINDO dispara')
"
```

## Acceptance

- Schema do `estado.json` migrado em 10/10 dossiês.
- 4 testes regressivos em `tests/test_dossie_tipo.py`: (a) primeira graduação com divergente ativa dispara REGREDINDO; (b) graduação limpa não dispara; (c) revalidar OK limpa `divergencias_ativas`; (d) histórico nunca apaga.
- `cupom_fiscal_foto` mantém status GRADUADO após backfill.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (s) Validação ANTES — grep + leitura do estado.json antes de codar.
- (cc) Refactor revela teste frágil — esperar que testes regressivos do dossie precisem update.
- (o) Subregra retrocompatível — migrador idempotente roda 1× e é noop nas próximas.

---

*"Confundir histórico com estado atual é apagar o próprio sensor." — princípio do observador honesto*
