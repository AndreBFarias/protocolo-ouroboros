---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 21
  title: "Relatórios Diagnósticos: do descritivo ao comparativo"
  touches:
    - path: src/load/relatorio.py
      reason: "novo template diagnóstico YYYY-MM_diagnostico.md; relatório descritivo atual vira apêndice"
    - path: src/load/formatacao_md.py
      reason: "helpers para tabelas comparativas (delta, percentual, flag)"
    - path: mappings/metas.yaml
      reason: "saldo acumulado no ano vs meta exige leitura das metas existentes"
    - path: run.sh
      reason: "flag --diagnostico já coberta por --mes; não adicionar nova"
  n_to_n_pairs:
    - [src/load/relatorio.py, src/load/formatacao_md.py]
  forbidden:
    - src/llm/  # Sprint 21 é puro pandas; narrativa LLM fica para Sprint 33
    - src/dashboard/  # UI é Sprint 20, não mexer aqui
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "make process"
      timeout: 300
    - cmd: ".venv/bin/pytest tests/test_relatorio_diagnostico.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "data/output/YYYY-MM_diagnostico.md existe para o mês corrente"
    - "Relatório contém seção 'Comparativo 3 meses' com categoria/classificação/pessoa"
    - "Flags automáticos ('gasto novo', 'cresceu >30%', 'sumiu') renderizados quando aplicável"
    - "Top 3 outliers por maior desvio presentes"
    - "Saldo acumulado no ano vs meta impresso"
    - "Aviso de cobertura parcial emitido quando meses têm menos de 5 transações"
    - "Relatório descritivo anterior aparece como apêndice no fim do arquivo"
    - "Acentuação PT-BR correta e zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 21 -- Relatórios Diagnósticos: do descritivo ao comparativo

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprint 22 (Consolidação), Sprint 23 (Verdade nos Dados)
**Desbloqueia:** Sprint 33 (Narrativa LLM)
**Issue:** --
**Implementa:** ADR-10 (Resiliência a Dados Incompletos) -- avisos de cobertura parcial em vez de crash
**ADR:** ADR-10

---

## Como Executar

**Comandos principais:**
- `make lint`
- `make process` -- pipeline completo gera o novo diagnóstico
- `./run.sh --mes 2026-03` -- gerar diagnóstico de um mês específico
- `.venv/bin/pytest tests/test_relatorio_diagnostico.py -x -q` (após Sprint 30)

### O que NÃO fazer

- NÃO introduzir LLM nesta sprint: comparações são puro pandas. Narrativa via LLM é Sprint 33.
- NÃO apagar o relatório descritivo atual: vira apêndice do diagnóstico.
- NÃO inventar cenários com dados ausentes -- usar o aviso "cobertura parcial".
- NÃO quebrar o sync Obsidian: frontmatter atual continua valendo (receita/despesa/saldo).

---

## Problema

O relatório mensal atual (`data/output/YYYY-MM_relatorio.md`) é descritivo: lista totais, top gastos e projeção linear. Não responde à pergunta que importa: "este mês foi normal ou anômalo?".

Um leitor (humano ou agente) não consegue distinguir entre:

- Mês em que farmácia cresceu 40% por motivo sazonal.
- Mês em que surgiu um gasto novo que ninguém notou.
- Mês em que um obrigatório sumiu silenciosamente.
- Mês em que a cobertura de dados está parcial (falta extrair Nubank PF, por exemplo).

Enquanto houver só descritivo, o ciclo de melhoria do sistema fica dependente da leitura humana. Com comparativo + flags automáticos, o próprio relatório já destaca o que merece atenção.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Relatório descritivo | `src/load/relatorio.py` | Gera `YYYY-MM_relatorio.md` com totais, top gastos, Mermaid chart, projeção |
| Formatação Markdown | `src/load/formatacao_md.py` | Helpers de tabela, badge, seção |
| Metas | `mappings/metas.yaml` | Metas com valor alvo e prazo |
| Projeção | `src/projections/__init__.py` | Média móvel de 3 meses |
| XLSX | `src/load/xlsx_writer.py` | Abas `extrato`, `resumo_mensal`, `irpf` (base de todo comparativo) |

---

## Implementação

### Fase 1: arquitetura do diagnóstico

**Arquivo:** `src/load/relatorio.py`

Nova função `gerar_relatorio_diagnostico(df: pd.DataFrame, mes_ref: str, metas: dict) -> str` que devolve markdown completo com seções:

1. **Cabeçalho** -- mês corrente, cobertura de dados (contagem de transações por banco).
2. **Sumário** -- receita, despesa, saldo (reaproveita lógica atual).
3. **Comparativo 3 meses** -- tabela por categoria, por classificação (Obrigatório/Questionável/Supérfluo/N/A), por pessoa. Colunas: mês corrente, média 3 meses, delta %, flag.
4. **Flags automáticos** -- lista com 3 tipos:
   - `NOVO` -- categoria que apareceu pela primeira vez em 3 meses.
   - `ALTA` -- categoria com delta > 30% para cima.
   - `SUMIU` -- categoria que existia nos 3 meses anteriores e zerou.
5. **Top 3 outliers** -- maior desvio absoluto em R$ frente à média (positivo ou negativo).
6. **Metas** -- saldo acumulado no ano dividido pelo valor-alvo de cada meta em `mappings/metas.yaml`. Percentual e velocidade ("no ritmo atual, atinge em N meses").
7. **Aviso de cobertura** -- se `df.loc[df.mes_ref == mes_ref].shape[0] < 5`, emitir bloco `> Aviso: mês com cobertura parcial -- análise limitada`.
8. **Apêndice: relatório descritivo** -- embutir o conteúdo atual de `gerar_relatorio_mes(df, mes_ref)` no fim.

### Fase 2: escrita no disco

**Arquivo:** `src/load/relatorio.py`

- Manter gravação de `data/output/YYYY-MM_relatorio.md` (descritivo, retrocompatível com Obsidian sync).
- Adicionar gravação de `data/output/YYYY-MM_diagnostico.md` com saída da nova função.
- Pipeline (`src/pipeline.py`) chama ambas.

### Fase 3: helpers de formatação

**Arquivo:** `src/load/formatacao_md.py`

- `tabela_comparativa(nome_coluna, mes_corrente, media, flag)` -- renderiza linha de tabela MD.
- `badge_flag("NOVO" | "ALTA" | "SUMIU")` -- textual, sem emoji. Exemplo: `**[ALTA +42%]**`.
- `bloco_aviso(texto)` -- `> Aviso: ...`.

### Fase 4: comparativo em pandas

**Arquivo:** `src/load/relatorio.py` (funções auxiliares)

- `comparar_categorias(df, mes_ref) -> pd.DataFrame`: pivota por categoria x mes_ref; calcula média dos 3 meses anteriores; calcula delta.
- `detectar_flags(df_comparativo) -> list[dict]`: aplica regras `NOVO`, `ALTA`, `SUMIU`.
- `top_outliers(df_comparativo, n=3) -> pd.DataFrame`: ordena por `abs(delta_abs)` desc.

### Fase 5: saldo acumulado vs meta

**Arquivo:** `src/load/relatorio.py`

- Ler `mappings/metas.yaml`.
- Somar saldos mensais do ano corrente.
- Para cada meta: `percentual = min(saldo_acumulado / meta.valor_alvo, 1.0)`.
- Velocidade: saldo acumulado / meses decorridos → projeção simples de quando atinge.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A21-1 | Meses de transição com novo banco geram flag `NOVO` falso-positivo | Janela de 3 meses com pelo menos 2 meses completos; senão flag ignorado |
| A21-2 | Delta % explode quando média anterior é zero | Proteger com `if media_anterior == 0 and corrente > 0: flag=NOVO` |
| A21-3 | `mappings/metas.yaml` pode estar vazio | Seção de metas omitida, sem crash |
| A21-4 | Relatório MD precisa ser lido por humano E por provedor de IA | Evitar tabelas largas; preferir blocos curtos seguidos de lista |
| A21-5 | Apêndice duplica Mermaid chart | Gerar apenas uma vez no cabeçalho; apêndice reusa referência |
| A21-6 | Cobertura parcial precisa ser detectada cedo | Check no início do `gerar_relatorio_diagnostico`; se poucas transações, retornar diagnóstico mínimo |
| A21-7 | Sincronização N-para-N: se nome do arquivo muda, Obsidian sync precisa ser atualizado | Manter `YYYY-MM_relatorio.md` como antes; diagnóstico é arquivo novo |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `make process` gera `data/output/YYYY-MM_diagnostico.md` para todos os meses
- [ ] Arquivo contém as 8 seções obrigatórias (inspeção manual em um mês de alta cobertura)
- [ ] Flag `NOVO`/`ALTA`/`SUMIU` aparece ao menos 1 vez em um relatório de teste
- [ ] Top 3 outliers renderizados com delta em R$
- [ ] Seção "Metas" mostra percentual e projeção
- [ ] Aviso de cobertura parcial aparece em mês com <5 transações
- [ ] Apêndice com relatório descritivo presente
- [ ] `python -m src.utils.validator` 6/6 OK
- [ ] Teste unitário `tests/test_relatorio_diagnostico.py` (criado na Sprint 30) passa

---

## Verificação end-to-end

```bash
make lint
make process
ls data/output/*_diagnostico.md | wc -l   # >= 1
./run.sh --mes 2026-03
python -m src.utils.validator
```

---

*"O que não se mede não se melhora, e o que não se compara não se entende." -- Lorde Kelvin (parafraseado)*
