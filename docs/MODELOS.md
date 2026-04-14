# Modelos de Dados -- Controle de Bordo

Documentação de todos os schemas utilizados no pipeline, incluindo tabelas do XLSX (8 abas) e dataclass interna.

---

## Dataclass Base: Transacao (`src/extractors/base.py`)

Representação interna de uma transação durante o pipeline. Todos os extratores produzem instâncias desta dataclass.

| Campo | Tipo | Obrigatório | Descrição | Exemplo |
|-------|------|-------------|-----------|---------|
| data | `date` | sim | Data da transação (ISO 8601) | `2026-04-05` |
| valor | `float` | sim | Valor em R$ (negativo = débito) | `-45.90` |
| descricao | `str` | sim | Descrição original do banco | `PIX ENVIADO - VITORIA` |
| banco_origem | `str` | sim | Banco de onde veio a transação | `nubank_cc` |
| pessoa | `str` | sim | Titular da conta/cartão | `André` |
| forma_pagamento | `str` | sim | Meio utilizado | `Pix` |
| tipo | `str` | sim | Natureza da transação | `Despesa` |
| identificador | `str \| None` | não | UUID único (quando disponível) | `abc123-def456` |
| arquivo_origem | `str` | sim | Nome do arquivo de onde foi extraída | `nubank_cc_2026-04.csv` |

---

## Aba: extrato

Tabela principal do XLSX. Cada linha representa uma transação processada, categorizada e classificada.

| Coluna | Tipo | Obrigatório | Descrição | Exemplo | Regras de Validação |
|--------|------|-------------|-----------|---------|---------------------|
| data | `date` | sim | Data da transação | `2026-04-05` | Formato ISO 8601. Deve estar dentro do mes_ref. |
| valor | `float` | sim | Valor absoluto em R$ | `45.90` | Sempre positivo. 2 casas decimais. |
| forma_pagamento | `str` | sim | Meio de pagamento | `Pix` | Enum: Pix, Débito, Crédito, Boleto, Transferência |
| local | `str` | sim | Nome do estabelecimento ou descrição | `IFOOD` | Descrição original normalizada (upper, sem espaços extras) |
| quem | `str` | sim | Responsável | `André` | Enum: André, Vitória, Casal |
| categoria | `str` | sim | Categoria do gasto | `Delivery` | Deve existir no mappings/categorias.yaml ou ser "Outros" |
| classificacao | `str` | sim | Nível de necessidade | `Questionável` | Enum: Obrigatório, Questionável, Supérfluo |
| banco_origem | `str` | sim | Banco de origem | `Nubank CC` | Identificador do extrator que gerou |
| tipo | `str` | sim | Natureza financeira | `Despesa` | Enum: Despesa, Receita, Transferência Interna, Imposto |
| mes_ref | `str` | sim | Mês de referência | `2026-04` | Formato YYYY-MM |
| tag_irpf | `str \| null` | não | Tag para declaração IRPF | `dedutivel_medico` | Atribuída pelo irpf_tagger. Null se não aplicável |
| obs | `str \| null` | não | Observações livres | `Parcela 3/12` | Texto livre. Preenchido por overrides ou manual |

---

## Aba: renda

Uma linha por mês por fonte de renda. Controle de receitas brutas e líquidas.

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| mes_ref | `str` | sim | Mês de referência | `2026-04` |
| fonte | `str` | sim | Origem da renda | `G4F` |
| bruto | `float` | sim | Valor bruto recebido | `8500.00` |
| inss | `float` | sim | Desconto INSS | `742.80` |
| irrf | `float` | sim | Desconto IRRF | `1050.00` |
| vr_va | `float` | sim | Vale refeição/alimentação | `1100.00` |
| liquido | `float` | sim | Valor líquido creditado | `6707.20` |
| banco | `str` | sim | Banco onde foi creditado | `Itaú` |

**Fontes conhecidas:** G4F, Infobase, PJ Vitória, Rendimentos.

---

## Aba: dividas_ativas

Snapshot mensal de contas fixas e dívidas. Atualizado a cada execução do pipeline.

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| mes_ref | `str` | sim | Mês de referência | `2026-04` |
| custo | `str` | sim | Nome da conta/dívida | `Aluguel` |
| valor | `float` | sim | Valor mensal | `800.00` |
| status | `str` | sim | Situação do pagamento | `Pago` |
| vencimento | `int` | sim | Dia do mês de vencimento | `10` |
| quem | `str` | sim | Responsável pelo pagamento | `Casal` |
| recorrente | `bool` | sim | Se repete todo mês | `True` |
| obs | `str \| null` | não | Observações | `Contrato até dez/2026` |

**Status possíveis:** Pago, Não Pago, Parcial.

---

## Aba: inventario

Bens do casal com cálculo de depreciação. Atualizado manualmente.

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| bem | `str` | sim | Nome do bem | `Notebook Dell` |
| valor_aquisicao | `float` | sim | Valor pago na compra | `4500.00` |
| vida_util_anos | `int` | sim | Vida útil estimada em anos | `5` |
| depreciacao_anual | `float` | sim | Perda de valor por ano | `900.00` |
| perda_mensal | `float` | sim | Perda de valor por mês | `75.00` |

**Cálculo:** `depreciacao_anual = valor_aquisicao / vida_util_anos`. `perda_mensal = depreciacao_anual / 12`.

---

## Aba: prazos

Vencimentos recorrentes para controle de agenda financeira.

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| conta | `str` | sim | Nome da conta | `Energia (CEB)` |
| dia_vencimento | `int` | sim | Dia do mês | `15` |
| banco_pagamento | `str` | sim | Banco usado para pagar | `Itaú` |
| auto_debito | `bool` | sim | Se está em débito automático | `False` |

---

## Aba: resumo_mensal

Gerada automaticamente pelo pipeline. Uma linha por mês processado.

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| mes_ref | `str` | sim | Mês de referência | `2026-04` |
| receita_total | `float` | sim | Soma de todas as receitas do mês | `12500.00` |
| despesa_total | `float` | sim | Soma de todas as despesas do mês | `8900.00` |
| saldo | `float` | sim | receita_total - despesa_total | `3600.00` |
| top_categoria | `str` | sim | Categoria com maior gasto | `Aluguel` |
| top_gasto | `str` | sim | Maior transação individual | `Aluguel Ki-Sabor R$800` |
| total_obrigatorio | `float` | sim | Soma de gastos obrigatórios | `5200.00` |
| total_superfluo | `float` | sim | Soma de gastos supérfluos | `1800.00` |
| total_questionavel | `float` | sim | Soma de gastos questionáveis | `1900.00` |

---

## Aba: irpf

Dados acumulados para declaração de imposto de renda. Gerada pelo irpf_tagger.

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ano | `int` | sim | Ano-calendário | `2026` |
| tipo | `str` | sim | Tipo do registro IRPF | `rendimento_tributavel` |
| fonte | `str` | sim | Fonte pagadora ou prestadora | `G4F Soluções` |
| cnpj_cpf | `str` | sim | CNPJ ou CPF da fonte | `12.345.678/0001-90` |
| valor | `float` | sim | Valor acumulado | `8500.00` |
| mes | `str` | sim | Mês de referência | `2026-04` |

**Tipos possíveis (5):** `rendimento_tributavel`, `inss`, `irrf`, `despesa_medica`, `imposto_pago`.

---

## Aba: analise

Texto livre gerado pelo pipeline com insights do mês.

| Coluna | Tipo | Obrigatório | Descrição |
|--------|------|-------------|-----------|
| conteudo | `str` | sim | Texto Markdown com análise, alertas e recomendações |

Esta aba contém uma única célula com texto formatado incluindo: resumo financeiro, top 5 categorias, comparativo com mês anterior, alertas de gastos atípicos, transferências internas, IRPF acumulado e projeção.

---

## Relacionamentos entre Abas

```
extrato.mes_ref -----> resumo_mensal.mes_ref (agregação)
extrato.mes_ref -----> dividas_ativas.mes_ref (snapshot)
extrato.tag_irpf ----> irpf.tipo (classificação fiscal)
renda.mes_ref -------> resumo_mensal.receita_total (soma)
prazos.conta --------> dividas_ativas.custo (referência)
```

Não há foreign keys formais (XLSX não suporta). A consistência é mantida pelo pipeline e validada pelo `validator.py`.

---

*"Medir o que é mensurável e tornar mensurável o que não é." -- Galileu Galilei*
