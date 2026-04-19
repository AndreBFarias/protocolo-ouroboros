## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 23
  title: "Verdade nos Dados: encerrar resíduo de abas fantasmas e CNPJ"
  touches:
    - path: src/load/xlsx_writer.py
      reason: "aba renda decide entre remoção de inss/irrf/vr_va ou carga via YAML; aba analise ganha cabeçalho DEPRECATED; abas dividas_ativas/inventario/prazos ganham cabeçalho de snapshot 2023"
    - path: src/transform/irpf_tagger.py
      reason: "expandir linhas 177-197 para extrair CNPJ contextual em textos de Itaú e Nubank PDF"
    - path: src/extractors/itau_pdf.py
      reason: "capturar CNPJ do contraparte no parsing de descrição"
    - path: src/extractors/nubank_pdf.py
      reason: "capturar CNPJ do contraparte no parsing de descrição"
    - path: src/projections/__init__.py
      reason: "corrigir bug de --mes que passa dados já filtrados para gerar_relatorios"
    - path: src/pipeline.py
      reason: "passar transações completas para gerar_relatorios mesmo quando --mes filtra o extrato"
    - path: mappings/contracheques/EXEMPLO.yaml
      reason: "template opcional para entrada manual de INSS/IRRF/VR-VA até Sprint 24"
    - path: CLAUDE.md
      reason: "refletir decisão final sobre aba renda, marcar análise como DEPRECATED"
  n_to_n_pairs:
    - [src/load/xlsx_writer.py, CLAUDE.md]
    - [src/transform/irpf_tagger.py, src/extractors/itau_pdf.py]
    - [src/transform/irpf_tagger.py, src/extractors/nubank_pdf.py]
  forbidden:
    - src/dashboard/  # UI é Sprint 20/21, não mexer aqui
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "make process"
      timeout: 300
    - cmd: "python -m src.utils.validator"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_irpf_tagger.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Aba renda não gera colunas permanentemente vazias (inss/irrf/vr_va removidas OU alimentadas por mappings/contracheques/*.yaml)"
    - "Aba irpf tem ao menos 10 linhas com cnpj_cpf preenchido"
    - "Aba analise tem primeira célula com prefixo '[DEPRECATED -- ver relatório diagnóstico Sprint 21]'"
    - "Abas dividas_ativas, inventario, prazos têm cabeçalho 'Snapshot histórico 2023'"
    - "Bug --mes corrigido: projeção usa 3 últimos meses, não 1"
    - "CLAUDE.md reflete decisão sobre colunas de renda"
    - "Acentuação PT-BR correta e zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 23 -- Verdade nos Dados: encerrar resíduo de abas fantasmas e CNPJ

**Status:** CONCLUÍDA
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Refactor
**Dependências:** Nenhuma
**Desbloqueia:** Sprint 30 (testes cobrem as mudanças)
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint` -- ruff + format + acentuação
- `make process` -- pipeline completo
- `python -m src.utils.validator` -- 6 checagens de integridade
- `.venv/bin/pytest tests/test_irpf_tagger.py -x -q` -- regras IRPF (após Sprint 30)

### O que NÃO fazer

- NÃO remover a aba `analise`: apenas marcar como DEPRECATED até a Sprint 33 (narrativa LLM).
- NÃO apagar `dividas_ativas`, `inventario` ou `prazos`: estão congelados, mas são referenciados pelo dashboard.
- NÃO mudar o esquema das colunas obrigatórias de `extrato` (compatibilidade com Obsidian sync e relatório).
- NÃO adicionar dependência nova.

---

## Problema

O XLSX tem quatro classes de mentira silenciosa, documentadas em `CLAUDE.md` seção "Lacunas conhecidas":

1. **Aba `renda`:** colunas `inss`, `irrf`, `vr_va` são emitidas sempre vazias porque não há extrator de contracheque. Usuário abre o arquivo e pensa que a aba tem dado -- não tem.
2. **Aba `analise`:** produz frases genéricas ("Total de X transações, Y receita"). Não é análise. Dá impressão de inteligência inexistente.
3. **Aba `irpf`:** a coluna `cnpj_cpf` é sempre vazia. Para uso real no IRPF, esse dado é obrigatório.
4. **Abas `dividas_ativas`, `inventario`, `prazos`:** congeladas em 2023. Dashboard mostra como se fossem ativas.

Além disso, herdado da Sprint 19: quando `./run.sh --mes YYYY-MM` é usado, `gerar_relatorios()` recebe transações já filtradas. A projeção que deveria usar média dos 3 últimos meses usa apenas 1.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| XLSX writer | `src/load/xlsx_writer.py` | 8 abas, schema documentado em `CLAUDE.md` |
| IRPF tagger | `src/transform/irpf_tagger.py:177-197` | Regras para detectar tipo e fonte, mas nunca preenche cnpj_cpf |
| Extrator Itaú PDF | `src/extractors/itau_pdf.py` | Usa pdfplumber + senha; descrição bruta tem CNPJ em muitos casos |
| Extrator Nubank PDF | `src/extractors/nubank_pdf.py` | Idem, descrição carrega CNPJ em pagamentos e boletos |
| Projeção | `src/projections/__init__.py` | Média móvel de 3 meses para receita/despesa |
| Pipeline | `src/pipeline.py` | Orquestra 11 passos; filtragem de --mes acontece antes de `gerar_relatorios` |

---

## Implementação

### Fase 1: aba `renda` -- decisão e execução

**Decisão recomendada:** remover as colunas `inss`, `irrf`, `vr_va` do emissor até a Sprint 24 habilitar extrator de contracheque. Motivo: colunas permanentemente vazias são mentira pior do que ausência.

Opcional (segundo caminho): criar `mappings/contracheques/EXEMPLO.yaml` com estrutura:

```yaml
mes_ref: "2026-04"
fonte: "G4F"
bruto: 0.00
inss: 0.00
irrf: 0.00
vr_va: 0.00
```

Se o arquivo `mappings/contracheques/{mes_ref}.yaml` existir, `xlsx_writer` preenche as colunas. Caso contrário, emite apenas `mes_ref`, `fonte`, `bruto`, `liquido`, `banco`.

**Arquivo:** `src/load/xlsx_writer.py` -- função que monta `df_renda`.

### Fase 2: aba `analise` -- marcar DEPRECATED

**Arquivo:** `src/load/xlsx_writer.py` (função que escreve aba `analise`).

Primeira célula da aba (linha 1, coluna A) recebe:

```
[DEPRECATED -- ver relatório diagnóstico da Sprint 21. Aba mantida para compatibilidade até Sprint 33.]
```

Manter o conteúdo atual abaixo. Dashboard precisa ignorar a primeira linha ao ler a aba.

### Fase 3: abas congeladas

**Arquivo:** `src/load/xlsx_writer.py`

Para `dividas_ativas`, `inventario`, `prazos`: primeira linha da aba leva a string:

```
[Snapshot histórico 2023 -- dados não são atualizados automaticamente. Sprint 24 decide reabilitar.]
```

### Fase 4: aba `irpf` -- extrair CNPJ contextual

**Arquivos:** `src/transform/irpf_tagger.py`, `src/extractors/itau_pdf.py`, `src/extractors/nubank_pdf.py`.

Passos:

1. Adicionar regex robusta no tagger: `CNPJ_REGEX = re.compile(r"\b(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b")` e `CPF_REGEX = re.compile(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2})\b")`.
2. No extrator Itaú PDF: preservar campo `descricao_bruta` original (hoje é normalizada). Guardar em coluna auxiliar `_raw_desc`.
3. No tagger IRPF, ao aplicar regras (linhas 177-197), rodar regex contra `_raw_desc` e preencher `cnpj_cpf` quando casar. Normalizar para formato `XX.XXX.XXX/XXXX-XX` ou `XXX.XXX.XXX-XX`.
4. Nunca inventar CNPJ: se não casar, deixa vazio.

### Fase 5: bug do `--mes`

**Arquivos:** `src/pipeline.py`, `src/load/relatorio.py`.

Refatorar o fluxo para que `gerar_relatorios()` receba sempre o dataframe completo mais o filtro de mês como argumento separado. `relatorio.py` filtra para a seção do mês mas usa o dataframe completo para projeção.

### Fase 6: sincronizar documentação

**Arquivo:** `CLAUDE.md`

Atualizar a seção "Schema do XLSX" para refletir a decisão da Fase 1 e os cabeçalhos DEPRECATED/snapshot.
Atualizar "Lacunas conhecidas": remover `INSS/IRRF/VR-VA vazios` (ou alterar para "opt-in via YAML") e `cnpj_cpf vazio`.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A23-1 | Remover colunas do XLSX pode quebrar código do dashboard que acessa pelo nome | Buscar referências (`grep -R "inss\|irrf\|vr_va" src/dashboard/`) antes de remover |
| A23-2 | Dashboard lê `dividas_ativas` na aba Contas | Não remover aba; apenas cabeçalho DEPRECATED |
| A23-3 | CNPJ tem formatos variados (com e sem pontuação) | Normalizar após extrair para formato canônico |
| A23-4 | Regex `CONSULT` casa "consultoria TI" e "consulta médica" (armadilha histórica) | Nunca inferir CNPJ do nome; só aceitar se regex de dígitos casar |
| A23-5 | `_raw_desc` pode ser NaN em extratores CSV (Nubank cartão) | `if pd.isna(raw)` antes do regex |
| A23-6 | Bug do `--mes` pode reaparecer se outro caller chamar `gerar_relatorios` com df filtrado | Documentar contrato da função no docstring |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `make process` concluído sem crash
- [ ] Aba `renda` do XLSX gerado não tem colunas permanentemente vazias (inspeção manual ou teste automatizado)
- [ ] Aba `irpf` tem `>= 10` linhas com `cnpj_cpf` preenchido (`pandas.read_excel(...).irpf.cnpj_cpf.notna().sum() >= 10`)
- [ ] Aba `analise` primeira célula começa com `[DEPRECATED`
- [ ] `./run.sh --mes 2026-03` produz projeção baseada em 3 meses, não 1
- [ ] `python -m src.utils.validator` com 6/6 checagens OK
- [ ] `CLAUDE.md` atualizado e sincronizado com `ROADMAP.md`

---

## Verificação end-to-end

```bash
make lint
make process
python -m src.utils.validator
./run.sh --mes 2026-03
python -c "import pandas as pd; df=pd.read_excel('data/output/extrato_consolidado.xlsx', sheet_name='irpf'); assert df.cnpj_cpf.notna().sum() >= 10, 'CNPJ insuficiente'; print('irpf ok')"
```

---

*"Aquele que não conhece a si mesmo engana-se primeiro na própria contabilidade." -- Sêneca*
