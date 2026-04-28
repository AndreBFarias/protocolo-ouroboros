## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 95b
  title: "Linker aceita âncora temporal alternativa por tipo (vencimento vs data_emissao)"
  prioridade: P3
  estimativa: ~2h
  origem: "achado colateral ACH95-2 durante execução da Sprint 95"
  touches:
    - path: src/graph/linking.py
      reason: "linhas 259-264 -- janela hoje é centrada em data_emissao apenas"
    - path: mappings/linking_config.yaml
      reason: "nova chave por tipo: ancora_temporal: data_emissao | vencimento"
    - path: tests/test_linking_runtime.py
      reason: "regressão: DAS PARCSN com vencimento vs data_emissao"
  forbidden:
    - "Quebrar comportamento default (data_emissao) para tipos que não declararem ancora alternativa"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_linking_runtime.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "DAS PARCSN com metadata.vencimento usa essa data como centro da janela quando ancora_temporal=vencimento no config"
    - "Reduz conflitos entre parcelas DAS PARCSN consecutivas (medir antes/depois: hoje 14 propostas pendentes)"
    - "Sprint 95 baseline mantida: 23 docs linkados continuam linkando"
  proof_of_work_esperado: |
    # Antes
    ls docs/propostas/linking/ | wc -l
    # Depois
    [aplicar fix + roda linker]
    ls docs/propostas/linking/ | wc -l
    # Esperado: redução de propostas de conflito (parcelas próximas resolvidas auto)
```

---

# Sprint 95b -- Linker âncora temporal alternativa

**Status:** CONCLUÍDA (2026-04-28, +3 testes 95b sem regressão)

## Resultado

`mappings/linking_config.yaml` ganhou chave opcional `ancora_temporal` por tipo. Default: `data_emissao`. DAS PARCSN agora declara `ancora_temporal: vencimento` -- mais cirúrgico para parcelas adjacentes.

`src/graph/linking.py:259-280`: lê `parametros.get("ancora_temporal", "data_emissao")`, busca `meta.get(ancora_campo)` e cai para `data_emissao` em fallback automático se o campo não existir no doc.

## Testes regressivos (`tests/test_linking_runtime.py` -- 5 -> 8)

- `test_sprint_95b_das_parcsn_usa_vencimento_como_ancora`: DAS PARCSN com data_emissao=2025-02-28 e vencimento=2025-04-30 + tx em 2025-04-25. Antes: delta=56d (cabe na janela 60d, score 0.72). Depois: delta=-5d (score 0.975). Confirma diff_dias do edge.
- `test_sprint_95b_holerite_default_ainda_usa_data_emissao`: holerite (sem `ancora_temporal` no config) continua centrado em data_emissao -- backward-compat preservado.
- `test_sprint_95b_ancora_inexistente_no_doc_cai_para_data_emissao`: DAS sem campo `vencimento` no metadata cai para `data_emissao` em vez de retornar lista vazia silenciosamente.

Backward-compat: tipos sem `ancora_temporal` no YAML continuam usando `data_emissao` (default). Os 5 testes pré-existentes do linker continuam verdes.
**Origem:** Achado colateral ACH95-2. Sprint 95 deixou 14 propostas de conflito pendentes em `docs/propostas/linking/` -- maioria parcelas DAS PARCSN consecutivas com top-1 e top-2 muito próximos. Janela de 60 dias centrada em `data_emissao` arrasta candidatas adjacentes. Centrar em `metadata.vencimento` (mais próximo da data real de pagamento PIX RECEITA FEDERAL) reduziria sobreposição.

## Motivação

DAS PARCSN tem dois marcadores temporais distintos:
- `data_emissao` -- quando a guia foi gerada (ex: 28/02/2026).
- `vencimento` -- quando deve ser paga (ex: 31/03/2026).

Pagamento PIX cai geralmente entre vencimento e vencimento+10. Janela centrada em data_emissao cobre 28/02 ± 60d = 30/12 a 29/04 -- arrasta parcela de janeiro e abril junto. Centrada em vencimento, 31/03 ± 30d = 01/03 a 30/04 -- mais cirúrgico.

## Escopo

### Fase 1 (30min)
Diagnóstico: quantas das 14 propostas pendentes envolvem parcelas adjacentes? Listar IDs.

### Fase 2 (1h)
Adicionar parâmetro `ancora_temporal` em `mappings/linking_config.yaml`:
```yaml
das_parcsn_andre:
  janela_dias: 60
  ancora_temporal: vencimento  # NOVO; default=data_emissao
  peso_temporal_diario: 0.005
  diff_valor_max: 0.05
```

Em `src/graph/linking.py`, função que constrói janela checa o config e usa `metadata.get(ancora)` em vez de hard-coded `metadata.data_emissao`.

### Fase 3 (30min)
Teste regressivo: dois DAS PARCSN com vencimentos adjacentes, tx PIX RECEITA FEDERAL no meio -- linker decide o correto baseado em vencimento, não em data_emissao.

## Armadilhas

- **Tipos sem `vencimento`** (holerite): default mantém `data_emissao`. Não pode quebrar.
- **Decisões já registradas:** propostas em `docs/propostas/linking/` são MD pendentes de aprovação humana. Não automaticamente resolver -- usuário confirma cada uma.

## Dependências

- Sprint 95 já em main.
- Sprint 95a (líquido em holerite) é independente -- pode ser feita antes ou depois.

---

*"O calendário de quem paga não é o calendário de quem emite." -- princípio do tempo bifurcado*
