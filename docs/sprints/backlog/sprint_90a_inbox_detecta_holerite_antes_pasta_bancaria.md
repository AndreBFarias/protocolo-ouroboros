## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 90a
  title: "Inbox detecta holerite antes de aceitar pasta destino bancaria"
  prioridade: P0
  estimativa: 1-2h
  origem: "auditoria 2026-04-26 ETL -- 13 PDFs em andre/itau_cc/ e andre/santander_cartao/ são holerites G4F mal classificados"
  touches:
    - path: src/intake/registry.py
      reason: "regra holerite tem que ter prioridade especifico antes de bancario"
    - path: mappings/tipos_documento.yaml
      reason: "regra holerite ganha marcador 'Demonstrativo de Pagamento de Salario'"
    - path: tests/test_intake_holerite_prioridade.py
      reason: "regressao: PDF com 'Demonstrativo de Pagamento' classifica holerite, não itau/santander"
  forbidden:
    - "Mover arquivos de raw/ existentes (tarefa de migração retroativa fica em Sprint 98)"
    - "Mexer no extrator contracheque_pdf"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_intake_holerite_prioridade.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Regra holerite em tipos_documento.yaml tem prioridade=especifico (antes de bancario_*)"
    - "PDF com primeira pagina contendo 'Demonstrativo de Pagamento de Salario' classifica como holerite"
    - "PDF Itau real (cabecalho 'ITAU UNIBANCO' agencia 6450) continua classificando como bancario_itau"
    - "Pelo menos 4 testes regressivos: holerite G4F, holerite Infobase, Itau real, Santander real"
  proof_of_work_esperado: |
    .venv/bin/python -c "
    from pathlib import Path
    from src.intake.preview import gerar_preview
    from src.intake.registry import detectar_tipo
    from src.intake.orchestrator import detectar_mime
    p = Path('data/raw/andre/itau_cc/BANCARIO_ITAU_CC_b1e59d77.pdf')
    mime = detectar_mime(p)
    txt = gerar_preview(p, mime) or ''
    d = detectar_tipo(p, mime, txt)
    print(f'Antes: tipo={d.tipo}')
    "
    # Antes: tipo=bancario_itau (errado)
    # Depois: tipo=holerite_g4f (correto)
```

---

# Sprint 90a -- Inbox detecta holerite antes de pasta bancaria

**Status:** BACKLOG (P0, criada 2026-04-26)
**Origem:** auditoria 2026-04-26 -- agente ETL detectou 13 PDFs em pastas bancarias erradas que são na verdade holerites G4F.

## Motivacao

13 PDFs unicos em `andre/itau_cc/` (3) e `andre/santander_cartao/` (10) são contracheques G4F (CNPJ 07.094.346/0002-26). O extrator bancario não consegue parsear (e não deveria, são holerites) entao retorna 0 transações -- mas o arquivo fica poluindo a pasta. O grafo extrai os 24 holerites corretos via `processar_holerites` que escaneia diretamente `data/raw/andre/holerites/`.

Causa raiz: o `inbox_processor` não detectou "Demonstrativo de Pagamento de Salario" no preview e o classifier deixou cair em fallback bancario por nome do arquivo (download era `extrato_<data>.pdf` que parecia bancario). Sistema veio salvar a pessoa pelo `processar_holerites` mas a pasta bruta ficou contaminada.

## Escopo

### Fase 1 -- Adicionar regra holerite com prioridade alta

`mappings/tipos_documento.yaml`:

```yaml
holerite_g4f:
  prioridade: especifico
  match_mode: any
  mime: ['application/pdf']
  regras:
    - requer_qualquer:
        - 'Demonstrativo de Pagamento de Salário'
        - 'G4F SOLUCOES CORPORATIVAS'
        - 'CNPJ: 07.094.346/0002-26'
  destino_pasta: 'data/raw/andre/holerites/'
  rename: 'HOLERITE_G4F_<sha8>.pdf'

holerite_infobase:
  prioridade: especifico
  match_mode: any
  mime: ['application/pdf']
  regras:
    - requer_qualquer:
        - 'INFOBASE'
        - 'CNPJ: <CNPJ_INFOBASE>'  # mascarado
  destino_pasta: 'data/raw/andre/holerites/'
  rename: 'HOLERITE_INFOBASE_<sha8>.pdf'
```

### Fase 2 -- Garantir prioridade no `registry.py`

Verificar que `registry.py::detectar_tipo` itera regras em ordem de prioridade `especifico > normal > fallback`. Se holerite_g4f e holerite_infobase tem `prioridade: especifico`, eles casam ANTES de bancario_*.

### Fase 3 -- Testes regressivos

`tests/test_intake_holerite_prioridade.py`:
1. PDF sintetico com "Demonstrativo de Pagamento de Salario" + "G4F" -> classifica `holerite_g4f`.
2. PDF sintetico com cabecalho "ITAU UNIBANCO" agencia 6450 -> classifica `bancario_itau` (regression).
3. PDF Santander real -> `bancario_santander` (regression).
4. PDF Infobase sintetico -> `holerite_infobase`.

## Armadilhas

- **CNPJ Infobase eh PII** -- não commitar valor real no YAML. Usar regex generica ou referencia a `mappings/pessoas.yaml` (gitignored).
- **Order matters em yaml**: regras `prioridade: especifico` devem aparecer antes das `prioridade: normal`. Confirmar `registry.py` itera nessa ordem.
- **Fixtures sinteticas**: criar PDFs minimos com reportlab (1 pagina cada). Não usar PDFs reais com PII.

## Dependencias

- Nenhuma. Independente das Sprints 95/96/97.

## Pos-fix

Sprint 98 (renomeacao retroativa) cuida de mover os 13 PDFs ja existentes em `itau_cc/` e `santander_cartao/` para `holerites/`. Esta Sprint 90a so previne problema futuro.

---

*"Holerite tem cara de holerite, não importa o nome do download." -- principio do match-pelo-conteúdo*
