---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 104
  title: "Reextracao em lote de documentos catalogados (--forcar-reextracao)"
  prioridade: P1
  estimativa: ~3h
  origem: "ESTADO_ATUAL.md backlog -- evolucao natural pos-Sprint 95a (extratores ganharam campos novos como 'liquido' que precisam chegar ao grafo)"
  touches:
    - path: scripts/reprocessar_documentos.py
      reason: "adicionar flag --forcar-reextracao + funcao _limpar_documentos_e_arestas"
    - path: run.sh
      reason: "wrapper --reextrair-tudo com confirmação interativa"
    - path: scripts/menu_interativo.py
      reason: "opção 6 no menu via ./run.sh --reextrair-tudo"
    - path: tests/test_sprint_104_reextracao_lote.py
      reason: "regressão: limpeza correta + preservação de outros nodes + opção menu"
    - path: tests/test_menu_interativo.py
      reason: "atualizar contagem de OPCOES_MENU (5 -> 6 + R + 0)"
  forbidden:
    - "Apagar nodes que NAO sao 'documento' (transação, fornecedor, item, categoria)"
    - "Modificar comportamento default sem a flag"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_sprint_104_reextracao_lote.py tests/test_menu_interativo.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Flag --forcar-reextracao limpa nodes 'documento' + 4 tipos de arestas (documento_de, fornecido_por, ocorre_em, contem_item)"
    - "Sem a flag, comportamento padrão idempotente preservado"
    - "Outros tipos de node (transação, fornecedor, periodo, item, categoria) intactos"
    - "run.sh --reextrair-tudo solicita confirmação interativa antes de executar"
    - "Menu interativo opção 6 dispara o mesmo fluxo"
    - "8 testes regressivos novos passam"
  proof_of_work_esperado: |
    .venv/bin/pytest tests/test_sprint_104_reextracao_lote.py -v
    # 8 passed
    
    grep "forcar-reextracao\|--reextrair-tudo" scripts/reprocessar_documentos.py run.sh
    # ambos referenciam a flag e o wrapper
```

---

# Sprint 104 -- Reextração em lote

**Status:** CONCLUÍDA (2026-04-28, +8 testes 104 sem regressão)

## Motivação

A Sprint 95a (commit b33fb1f) adicionou os campos `bruto` e `liquido` ao metadata do node holerite no grafo. Mas o pipeline existente é **idempotente por chave canônica** (`INSERT OR IGNORE` em `db.upsert_node`): ao reprocessar um holerite cuja chave já existe no grafo, o metadata novo é **descartado**. Sem reextração forçada, os 24 holerites já catalogados nunca vão ganhar `metadata.liquido` em runtime real.

Mesma armadilha vai acontecer toda vez que um extrator ganhar campo novo. Sprint 104 dá ao supervisor a ferramenta para forçar refresh.

## Implementação

### 1. `scripts/reprocessar_documentos.py`

Nova flag `--forcar-reextracao`. Quando ativada, antes de iterar sobre os arquivos, chama `_limpar_documentos_e_arestas(grafo)` que remove em SQL bruto:

```python
DELETE FROM edge WHERE tipo IN
  ('documento_de', 'fornecido_por', 'ocorre_em', 'contem_item')
  AND src_id IN (SELECT id FROM node WHERE tipo='documento');

DELETE FROM node WHERE tipo='documento';
```

Outros nodes (`transacao`, `fornecedor`, `periodo`, `item`, `categoria`, `produto_canonico`) **permanecem intactos** — são re-vinculados pelos extratores conforme reingerem.

### 2. `run.sh --reextrair-tudo`

Wrapper interativo. Solicita `confirmar "Tem certeza? (operação irreversivel)"` antes de chamar o script. Não roda sem confirmação humana — proteção contra `--reextrair-tudo` digitado por engano.

### 3. `scripts/menu_interativo.py` opção 6

```
6 - Reextrair documentos (limpa grafo e re-ingere) [Sprint 104]
```

Delega para `./run.sh --reextrair-tudo`. Atualizado teste `test_opcoes_menu_tem_seis_mais_rota_completa_e_saida` (renomeado de `_cinco_mais_*` ; agora valida 8 chaves em OPCOES_MENU).

## Testes regressivos (`tests/test_sprint_104_reextracao_lote.py` -- 8 novos)

1. `test_limpar_documentos_apaga_3_docs_e_4_edges` -- contagem correta no cenário canônico.
2. `test_limpar_documentos_preserva_outros_nodes` -- não apaga fornecedor/periodo/transação.
3. `test_limpar_documentos_preserva_outras_arestas` -- aresta `categoria_de` (item->categoria) e `vendeu` permanecem.
4. `test_limpar_documentos_idempotente` -- rodar 2x não levanta nem dá contagem negativa.
5. `test_run_sh_help_inclui_reextrair` -- help do shell menciona a flag.
6. `test_menu_interativo_inclui_opcao_6` -- texto e dispatcher conferem.
7. `test_argparse_aceita_forcar_reextracao_sem_levantar` -- parse OK em --dry-run.
8. `test_metadata_atualizado_chega_apos_reextracao` -- cenário canônico Sprint 95a (holerite ganha `liquido`).

## Resultado

| Métrica | Antes | Depois |
|---|---|---|
| `pytest` baseline | 1.892 passed | **1.903 passed** (+11: 8 novos da 104 + 3 da 95b) |
| `make lint` | exit 0 | **exit 0** |
| `make smoke` | 8/8 + 23/23 | **8/8 + 23/23** |
| Flags `reprocessar_documentos.py` | 3 (`--dry-run`, `--raiz`, `--grafo`) | 4 (+`--forcar-reextracao`) |
| Opções menu interativo | 7 (`R`, 1-5, 0) | **8** (+6) |

## Próximos passos sugeridos (não escopo desta sprint)

- Quando dono autorizar, rodar `./run.sh --reextrair-tudo` em runtime real para que os 24 holerites recebam `metadata.liquido` e o linker (Sprint 95) possa apertar `diff_valor` de 0.30 para 0.05.
- Considerar Sprint 104b: reextração SELETIVA por tipo de documento (`--forcar-reextracao=holerite`) em vez de all-or-nothing.

---

*"As vezes precisa apagar o passado para ouvir o presente." -- princípio do reset-controlado*
