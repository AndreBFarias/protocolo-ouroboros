---
titulo: Investigacao -- Salario G4F R$ 6.381,14 categorizado como Transferencia no C6
data: 2026-05-12
sprint: INFRA-CATEGORIZAR-SALARIO-G4F-C6
status: CONCLUIDA
origem: docs/auditorias/VALIDACAO_ARTESANAL_HOLERITE_2026-05-12.md (ressalva 2)
---

# Investigacao -- drift de categorizacao Salario G4F no C6

## TL;DR

Hipotese **B** (regra de override estrutural) confirmada e implementada. Hipotese A
(importar extrato Santander) fica como sprint-filha porque depende de extrato bancario
que o dono ainda nao forneceu. Hipotese C (tag manual via revisor) foi descartada por
ser um fallback que so atrasa a recuperacao do drift.

## Evidencia coletada

### 1. Conta Santander de Andre nao esta importada

```
$ ls data/raw/andre/ | grep -i santander
(vazio)
```

O holerite G4F fev/2026 declara que o credito e feito em:

```
Conta: Banco 33 - Santander S.A., Agencia 2327, CC 71018701-1
```

Nenhum arquivo da pasta `data/raw/andre/` contem extrato Santander. Logo o salario
**nao entra no pipeline pela porta Santander** -- so chega ao ETL via transferencia
interna para o C6 do Andre.

### 2. Lancamentos no XLSX -- categoria errada e tag IRPF vazia

Confirmado pela auditoria HOLERITE 2026-05-12:

| data       | valor     | mes_ref  | categoria        | quem     | banco_origem |
|------------|-----------|----------|------------------|----------|--------------|
| 2026-03-06 | 6.381,14  | 2026-03  | Transferencia    | pessoa_a | C6           |
| 2026-03-06 | 6.381,14  | 2026-03  | Transferencia    | pessoa_a | C6           |

Tag IRPF: vazia em ambos. Categoria correta esperada: `Salario` com
`tag_irpf = rendimento_tributavel`.

### 3. Regex `categorias.yaml` ja contempla "G4F" mas a descricao bruta NAO

```yaml
salario:
  regex: "PAGTO.*SALARIO|CREDITO.*SALARIO|G4F|INFOBASE"
```

Logo a descricao do lancamento C6 nao contem nenhum dos tokens. Inspecao do
`categorizer.py` confirma que o match e por substring no campo
`_descricao_original` + `local` -- inadequado para transferencias internas.

### 4. Lancamento duplicado em 06/03/2026

A duplicacao (2 ocorrencias identicas) sera tratada na sprint paralela
`INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F` (outro executor).

## Decisao -- Opcao B com extensao de schema

### Por que B (e nao A ou C)

- **A (importar Santander)**: depende de extrato Santander que o dono nao forneceu.
  Promovida a sprint-filha `INFRA-IMPORTAR-SANTANDER-ANDRE` para quando o input chegar.
- **B (override estrutural)**: ataca o drift hoje sem dependencia externa, com filtros
  combinatorios robustos. Tem custo de extensao do `Categorizer` (~40 linhas
  retrocompat) e regra unica em `overrides.yaml`.
- **C (tag manual)**: empurra o trabalho para o revisor todo mes. Anti-padrao.
  Reservado como fallback se B falhar em casos extraordinarios.

### Mudancas implementadas

1. `src/transform/categorizer.py`:
   - Suporte a campos opcionais em overrides: `banco_origem`, `valor_min`,
     `valor_max`, `dia_min`, `dia_max`, `match_descricao_vazia`.
   - Novo metodo `_verificar_filtros_estruturais`.
   - `_aplicar_override` honra filtros estruturais quando declarados; aceita
     marcador "sentinela" como descricao se `match_descricao_vazia: true`.

2. `mappings/overrides.yaml` -- nova entrada:
   ```yaml
   "__SALARIO_G4F_C6__":
     categoria: "Salário"
     tipo: "Receita"
     tag_irpf: "rendimento_tributavel"
     banco_origem: "C6"
     valor_min: 6000
     valor_max: 7000
     dia_min: 1
     dia_max: 10
     match_descricao_vazia: true
   ```

3. `tests/test_categorizar_salario_g4f.py` -- 6 testes cobrindo:
   - aplicacao quando valor + banco + data batem;
   - nao-aplicacao se banco diferente (Itau);
   - nao-aplicacao se valor fora da faixa;
   - nao-aplicacao se data fora da janela (dia 25);
   - garantia de `tag_irpf = rendimento_tributavel` apos match;
   - limite inferior inclusivo (dia 1).

## Faixa e janela -- justificativa

- **Valor 6.000 a 7.000**: liquido Andre G4F oscila com IRRF/INSS mensalmente;
  R$ 6.381,14 observado em fev/2026, com folga para 13o salario reduzido / mes
  com mais descontos. Limite superior 7.000 evita falso-positivo em PIX de PJ
  PAIM (R$ 7.000+ recorrente).
- **Dia 1 a 10**: holerite declara `Data de pagamento: 06/03/2026`. Janela larga
  para feriado/final de semana.
- **banco_origem = C6**: exclusivo para a conta do Andre que recebe a TED do
  Santander. Quando o extrato Santander for importado (sprint A), esta regra
  pode ser retirada ou afinada.

## Validacao pos-mudanca

O re-run completo do pipeline depende de `data/output/ouroboros_2026.xlsx` (nao
presente no worktree). A validacao foi feita via testes unitarios que reproduzem
o cenario exato: 6 verdes em `test_categorizar_salario_g4f.py`. Regressao das suites
adjacentes (`test_categorizer.py`, `test_irpf_tagger.py`, `test_categorias_redesign.py`,
`test_irpf_regras_yaml.py`) sem quebras -- 34/34 verdes.

Re-run em ambiente do dono (com `data/output/`) e proximo passo natural; recomendado
em `make smoke` apos merge.

## Sprints-filhas abertas

- `INFRA-IMPORTAR-SANTANDER-ANDRE` (P2): adicionar extrator Santander quando o dono
  fornecer extratos. Apos esta sprint, a regra `__SALARIO_G4F_C6__` pode ser
  desativada (o salario entrara como `Salario` direto pelo regex G4F na descricao
  Santander).


# "O que sabemos e uma gota; o que ignoramos e um oceano." -- Isaac Newton
