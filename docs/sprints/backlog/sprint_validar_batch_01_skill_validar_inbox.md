---
id: VALIDAR-BATCH-01-SKILL-VALIDAR-INBOX
titulo: Sprint VALIDAR-BATCH-01 -- Skill `/validar-inbox` iterando fila pendente do
  CSV
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint VALIDAR-BATCH-01 -- Skill `/validar-inbox` iterando fila pendente do CSV

> **Slug ASCII para referência cruzada**: `validar_batch_01`. Em texto livre, usar "VALIDAR-BATCH-01".

**Origem**: prompt complementar do dono em 2026-04-29 (Gap 2 da sequência D7-extendida).
**Prioridade**: P2 (depende de volume mensurável -- ≥50 linhas pendentes no CSV justifica).
**Onda**: 2
**Esforço estimado**: 2h
**Depende de**: `VALIDAÇÃO-CSV-01` (commit 9504d4a) -- reusa `scripts/validar_arquivo.py` e `src/load/validacao_csv.py`.

## Problema

`/validar-arquivo` opera sobre um arquivo por vez (`--sha8 X --campo Y`). Para validar 20 NFC-e do mês, são 20 invocações sequenciais. Durante temporada IRPF (janeiro/fevereiro, 40-60 documentos novos), validação manual unitária vira gargalo crônico.

## Hipótese

Toda a infraestrutura necessária existe -- `validacao_csv.ler_csv()` retorna lista de `LinhaValidacao`, `validacao_csv.atualizar_validacao_opus()` aceita escrita unitária. Falta apenas iterador semântico que pré-filtre pendências e maximize fluência da minha leitura multimodal.

**Validar antes de codar**:
- `grep -n "validar_inbox\|validar.*batch" scripts/ src/` -- esperado: zero.
- Confirmar que `validar_arquivo.py --listar` já existe e retorna formato útil.
- Verificar se o CSV tem coluna `caminho_relativo` (evita re-resolver path).

## Implementação proposta

### Etapa 1 -- CLI `scripts/validar_inbox.py` (~45min)

Wrapper sobre `validar_arquivo.py`:

```bash
.venv/bin/python scripts/validar_inbox.py [--tipo X] [--mes YYYY-MM] [--apenas-divergentes] [--limite N]
```

Comportamento:

1. Lê CSV via `vc.ler_csv()`.
2. Filtra por `status_opus == "pendente"`.
3. Aplica filtros opcionais (`--tipo`, `--mes` extraído de `ts_processado`, `--apenas-divergentes` que requer `valor_etl != valor_humano` quando ambos preenchidos).
4. Agrupa por `sha8_arquivo` (1 arquivo pode ter 10 campos pendentes).
5. Para cada arquivo, imprime metadata em formato amigável para Opus interativo ler e usar Read multimodal.
6. Reporta progresso a cada N=5 arquivos: `[VAL-BATCH] 5/23 arquivos processados`.

### Decisão pendente do dono (modo learning, 5-10 linhas decisivas)

UX da iteração tem 2 variantes -- preciso da escolha do dono antes de implementar:

**Variante A -- Interativo (seguro)**:
```
[VAL-BATCH] arquivo 1/23: holerite_2025-12.pdf (sha8=abc12345)
[VAL-BATCH] campos pendentes: salario_bruto, inss, irrf, vr, va
[VAL-BATCH] aguardando Opus ler arquivo... (chame /validar-arquivo --sha8 abc12345)
```
Vantagem: Opus revisa 1 a 1, máxima fidelidade.
Desvantagem: ainda exige `/validar-arquivo` por arquivo -- batch é só pré-filtragem.

**Variante B -- Auto-batch (rápido)**:
```
[VAL-BATCH] arquivo 1/23: holerite_2025-12.pdf
  -> abrindo Read interno
  -> 5 campos validados (4 ok, 1 divergente)
[VAL-BATCH] arquivo 2/23: ...
```
Vantagem: 1 comando processa 23 arquivos.
Desvantagem: Opus precisa estar 100% confiante; sem confirmação humana intermediária.

Dono escolhe. Default proposto: **Variante A** (D7 prefere visibilidade humana sobre velocidade).

### Etapa 2 -- Skill `/validar-inbox` (~30min)

`.claude/skills/validar-inbox/SKILL.md`:

- Quando usar: lote de arquivos novos no inbox, temporada IRPF, após sprint de extrator novo.
- Como invocar: `/validar-inbox --tipo holerite --mes 2026-01`.
- Fluxo: skill chama `scripts/validar_inbox.py` -> recebe lista -> aplica variante escolhida.
- Conforme ADR-13: EU (Opus interativo) leio arquivos. Sem cron, sem API.

### Etapa 3 -- Testes (~30min)

`tests/test_validar_inbox.py`:

1. `test_filtro_tipo_seleciona_apenas_holerites`.
2. `test_filtro_mes_extrai_de_ts_processado`.
3. `test_apenas_divergentes_pula_concordantes`.
4. `test_limite_respeitado`.
5. `test_agrupamento_por_sha8` (1 arquivo com 5 campos pendentes vira 1 entrada).
6. `test_progresso_reportado_a_cada_N` (smoke -- captura stdout, assert presença de `[VAL-BATCH]`).

### Etapa 4 -- Atualizar `docs/SUPERVISOR_OPUS.md` (~15min)

Adicionar entrada na tabela "pergunta -> skill":

| Pergunta do dono | Skill canônica |
|---|---|
| "tem muito arquivo no inbox para validar" | `/validar-inbox` |
| "valida tudo que eu joguei essa semana" | `/validar-inbox --mes <atual>` |

## Proof-of-work (runtime real)

Após popular CSV via `./run.sh --full-cycle`:

```
$ /validar-inbox --tipo nfce_modelo_65 --limite 3
[VAL-BATCH] 3 arquivos pendentes (filtro: tipo=nfce_modelo_65)
[VAL-BATCH] arquivo 1/3: NFCe_2026-04-19_atacadao.pdf (sha8=abc12345)
[VAL-BATCH] campos pendentes: chave_44, cnpj_emitente, total
[...]
[VAL-BATCH] processados 3/3 (3 ok, 0 divergente, 0 lacuna)
```

E inspeção do CSV mostra `valor_opus` preenchido para os 3 arquivos.

## Acceptance criteria

- `scripts/validar_inbox.py` criado e funcional.
- Skill `/validar-inbox` registrada.
- Variante de UX escolhida pelo dono e implementada.
- 6 testes passando + baseline pytest crescida.
- `docs/SUPERVISOR_OPUS.md` atualizado com 2 entradas novas.
- `make lint` exit 0, `make smoke` 10/10.
- Proof-of-work runtime em commit body.
- Spec movida para `concluidos/`.

## Gate anti-migué

(9 checks padrão -- ver `CLAUDE.md` Workflow Obrigatório.)

## Não-objetivos

- **Não fazer**: automatizar processamento (sem cron).
- **Não fazer**: substituir `/validar-arquivo` -- batch é wrapper, não fork.
- **Não fazer**: tocar em `validacao_csv.py` (interface estável).

---

*"Visibilidade > velocidade."*
