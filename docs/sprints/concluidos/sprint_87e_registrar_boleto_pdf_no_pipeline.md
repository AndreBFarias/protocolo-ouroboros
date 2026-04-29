---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 87e
  title: "Registrar ExtratorBoletoPDF em src/pipeline.py::_descobrir_extratores"
  depends_on:
    - sprint_id: 87.3
      artifact: "src/extractors/boleto_pdf.py"
  touches:
    - path: src/pipeline.py
      reason: "adicionar import + append em _descobrir_extratores, posição análoga ao DAS PARCSN"
    - path: tests/test_pipeline_extratores.py
      reason: "teste de discovery -- boleto_pdf deve aparecer na lista retornada"
  forbidden:
    - "Alterar assinatura de ExtratorBoletoPDF (contrato da Sprint 87.3 intacto)"
    - "Mudar ordem global -- boleto fica antes do catch-all recibo_nao_fiscal"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "src/pipeline.py::_descobrir_extratores retorna ExtratorBoletoPDF na lista"
    - "Posição: antes do ExtratorReciboNaoFiscal (catch-all), análoga a DAS PARCSN e DIRPF"
    - "./run.sh --tudo agora ingere boletos novos no grafo sem precisar de reprocessar_documentos.py"
    - "Baseline de testes mantida ou cresce"
  proof_of_work_esperado: |
    # Antes (estado pós-sessão 2026-04-23)
    grep -ci boleto src/pipeline.py  # = 0

    # Depois
    grep -ci boleto src/pipeline.py  # >= 2 (import + append)
    .venv/bin/python -c "from src.pipeline import _descobrir_extratores; assert any('Boleto' in e.__name__ for e in _descobrir_extratores())"
```

---

# Sprint 87e — registrar `ExtratorBoletoPDF` no pipeline principal

**Status:** BACKLOG (resolve P1-01 da Auditoria Técnica 2026-04-23)
**Prioridade:** P1 (boletos novos em inbox não viram docs no grafo sem intervenção manual)
**Tempo estimado:** 30min
**Origem:** HANDOFF_2026-04-24 "Ressalva técnica descoberta hoje" + `docs/auditoria_tecnica_2026-04-23.md` §P1-01

## Problema

`ExtratorBoletoPDF` foi criado na Sprint 87.3 e registrado em `scripts/reprocessar_documentos.py::EXTRATORES_DOCUMENTAIS`, mas **NÃO** em `src/pipeline.py::_descobrir_extratores`. Consequência: `./run.sh --tudo` roteia boletos corretamente via intake (Sprint 70) mas não os ingere no grafo -- o operador precisa rodar `python scripts/reprocessar_documentos.py` manualmente depois.

Evidência empírica:
```
grep -ci boleto src/pipeline.py  # = 0
```

Enquanto DAS PARCSN (P1.1 2026-04-23) e DIRPF (P3.1 2026-04-23) estão em AMBOS os discoverys, o boleto só está em um.

## Fix

Adicionar bloco idiomático em `src/pipeline.py::_descobrir_extratores` após DAS PARCSN e DIRPF:

```python
# Boleto PDF (Sprint 87.3 / 87e). Registrado antes do catch-all recibo_nao_fiscal.
try:
    from src.extractors.boleto_pdf import ExtratorBoletoPDF

    extratores.append(ExtratorBoletoPDF)
except ImportError as e:
    logger.warning("Extrator boleto_pdf indisponível: %s", e)
```

Posição: imediatamente após DIRPF, antes do bloco do `recibo_nao_fiscal` (catch-all).

## Teste

`tests/test_pipeline_extratores.py` (arquivo novo ou adicionar em arquivo existente):

```python
def test_discovery_inclui_boleto_pdf():
    from src.pipeline import _descobrir_extratores
    extratores = _descobrir_extratores()
    nomes = [e.__name__ for e in extratores]
    assert "ExtratorBoletoPDF" in nomes, (
        "ExtratorBoletoPDF deve estar registrado no pipeline. Sem isso, "
        "boletos novos não são ingeridos no grafo via ./run.sh --tudo."
    )
    # Ordem canonica: antes do recibo_nao_fiscal (catch-all)
    idx_boleto = nomes.index("ExtratorBoletoPDF")
    idx_recibo = nomes.index("ExtratorReciboNaoFiscal")
    assert idx_boleto < idx_recibo, "Boleto deve vir antes do recibo_nao_fiscal"
```

## Armadilhas

- Se o teste `tests/test_pipeline_extratores.py` não existe, criar. Do contrário, append no existente.
- Confirmar que Sprint P3.1 (DIRPF) já adicionou o bloco DIRPF antes -- o bloco de boleto vai DEPOIS do DIRPF.

---

*"Um extrator não-registrado é um extrator dormindo." -- princípio de discovery automático*
