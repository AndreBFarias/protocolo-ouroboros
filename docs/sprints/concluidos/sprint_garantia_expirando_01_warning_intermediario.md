---
concluida_em: 2026-05-01
diagnostico_revisado: bug duplo no teste, nao no extrator/ingestor; (a) caplog capturava logger errado (graph.ingestor_documento vs real graph.ingestor_especiais apos migracao Sprint ANTI-MIGUE-08); (b) teste nao congelava hoje, e fixture data_fim 2026-04-30 ja era EXPIRADA em runtime 2026-05-01
entrega_real: tests/test_garantia.py (xfail removido, parsea via _parse_garantia com hoje=2026-04-20, logger graph.ingestor_especiais, novo teste de regressao para vigente >30d), CHANGELOG entrada Fixed
testes: 2.177 passed -> 2.179 passed; 2 xfailed -> 1 xfailed
---

# Sprint GARANTIA-EXPIRANDO-01 -- Warning intermediario para garantia <=30 dias

> **Slug ASCII**: `garantia_expirando_01_warning_intermediario`. Texto livre: "GARANTIA-EXPIRANDO-01".

**Origem**: dívida pré-existente identificada em 2026-05-01 ao validar
baseline antes da sessão MOB-bridge. Teste
`tests/test_garantia.py::TestAlertaIngestor::test_ingestor_loga_warning_quando_expirando`
já falhava no HEAD `4f2bbb6` (não foi introduzido por commit recente).
Espera warning literal `"expira em ... <=30 dias"` mas o extrator
emite só `WARNING ... EXPIRADA em <data> -- não cobrável` quando o
prazo já estourou.

**Prioridade**: P2
**Onda**: 5 (Mobile bridge + cobertura documental)
**Esforço estimado**: 1h
**Depende de**: nada.

## Problema

`src/extractors/garantia.py` (Sprint 47b) não tem ramo intermediário:
ou a garantia ainda está vigente (sem warning), ou já está EXPIRADA
(warning final). Falta o ramo "expirando em N dias" para N <= 30
quando o prazo ainda não estourou mas está perto.

Em runtime: garantia que expira em 2026-04-30 (data do fixture) com
data de execução 2026-05-01 cai direto em EXPIRADA. Para o teste
passar, o extrator precisa também emitir warning intermediário em
data <= 30 dias antes do término.

## Hipótese para validação

O fix natural é em `garantia.py` adicionar branch:

```python
if prazo_termina_em_dias <= 30 and prazo_termina_em_dias > 0:
    logger.warning(
        "garantia %s (produto %s) expira em %d dias <=30 dias",
        nome, produto, prazo_termina_em_dias,
    )
```

ou similar. Validar com grep antes de codar.

## Critério de pronto

- [ ] `pytest tests/test_garantia.py::TestAlertaIngestor::test_ingestor_loga_warning_quando_expirando`
      passa sem `xfail`.
- [ ] Marker `@pytest.mark.xfail(...)` removido.
- [ ] Cobertura adicional: novo teste para garantia VIGENTE (>30 dias
      restantes) confirmando que NÃO emite warning intermediário.
- [ ] Sem regressão em `make test`.

*"Quem não avisa, não protege." -- princípio do alerta*
