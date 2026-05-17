---
id: AUDIT-CATEGORIA-REGRA-VALOR-SINAL
titulo: "Bug P0: `_verificar_regra_valor` usa valor com sinal, regra `<800` casa toda despesa"
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-17
fase: QUALIDADE
epico: 3
depende_de: []
esforco_estimado_horas: 1.5
origem: "auditoria independente 2026-05-17. Validação manual reproduziu o bug: transação KI-SABOR com valor -1000 (despesa de R$ 1000) é categorizada como Padaria (regra `<800`) em vez de Aluguel (regra `>=800`). Causa-raiz: `src/transform/categorizer.py::_verificar_regra_valor` compara `valor < 800` literal, e -1000 é menor que 800 → True. Toda despesa KI-SABOR vira Padaria, nenhuma Aluguel. Não é só KISABOR: TODA regra com `regra_valor` (>=800, <100, etc) está afetada quando aplicada a transações de despesa (valor negativo)."
---

# Sprint AUDIT-CATEGORIA-REGRA-VALOR-SINAL

## Contexto

Categorizer (`src/transform/categorizer.py`) suporta filtro por valor via `regra_valor`:

```yaml
aluguel_kisabor:
  regex: "PANIFICADORA.KI.SABOR|KISABOR"
  categoria: "Aluguel"
  regra_valor: ">=800"

padaria:
  regex: "PANIFICADORA|KI.SABOR|PAES|PADARIA"
  categoria: "Padaria"
  regra_valor: "<800"
```

Função `_verificar_regra_valor` (linha 107):

```python
"<": valor < limite_float,
```

Bug: `valor = -1000` (despesa). `-1000 < 800` retorna `True`. Logo qualquer despesa KI-SABOR casa "Padaria" (`<800`) e NUNCA casa "Aluguel" (`>=800`).

Validado runtime: 2026-05-17:

```
R$ 1000 (KI-SABOR despesa) -> categoria=Padaria  [BUG: esperado Aluguel]
R$ 500  (KI-SABOR despesa) -> categoria=Padaria  [OK]
```

## Hipótese e validação ANTES

```bash
.venv/bin/python <<EOF
from src.transform.categorizer import Categorizer
cat = Categorizer()
t1 = {"local": "PANIFICADORA KI-SABOR", "valor": -1000.0}
r1 = cat.categorizar_lote([t1])[0]
print(f"R\$1000 despesa -> {r1.get('categoria')}")  # Esperado: Aluguel
t2 = {"local": "PANIFICADORA KI-SABOR", "valor": -500.0}
r2 = cat.categorizar_lote([t2])[0]
print(f"R\$500 despesa -> {r2.get('categoria')}")  # Esperado: Padaria
EOF
```

Procurar outros sítios com `regra_valor`:

```bash
grep -c "regra_valor:" mappings/categorias.yaml mappings/overrides.yaml
```

## Objetivo

1. **Fix em `_verificar_regra_valor`**: usar `abs(valor)` para comparação:
   ```python
   valor_abs = abs(valor)
   operacoes = {
       ">=": valor_abs >= limite_float,
       "<": valor_abs < limite_float,
       ...
   }
   ```
   Justificativa: `regra_valor` declarada no YAML representa magnitude da transação, não sinal. Despesa de R$ 1000 e receita de R$ 1000 ambos devem casar `>=800`.

2. **Testes regressivos** em `tests/test_categorizer.py`:
   - `test_regra_valor_kisabor_despesa_1000_vira_aluguel`
   - `test_regra_valor_kisabor_despesa_500_vira_padaria`
   - `test_regra_valor_funciona_para_receita` (caso bordejante)
   - `test_regra_valor_sinal_negativo_nao_quebra_outras_regras`

3. **Auditoria retroativa**: rodar `python -m src.pipeline --tudo` apos fix. Comparar:
   - Antes: contagem de transações categorizadas como Aluguel
   - Depois: contagem deve aumentar (transações KI-SABOR de despesa que viraram Aluguel)
   - Log: `data/output/audit_categoria_regra_valor_sinal.json`

4. **Sprint-filha potencial**: re-rodar `make auditoria-xlsx` apos fix — categorias podem mudar para muitas transações.

## Não-objetivos

- Não tocar regex dos categorias.yaml.
- Não tocar lógica de classificação (Despesa/Receita/TI).
- Não criar novas regras — só fixar a comparação existente.

## Proof-of-work runtime-real

```bash
# Antes (reproduz bug):
.venv/bin/python -c "
from src.transform.categorizer import Categorizer
t = {'local': 'PANIFICADORA KI-SABOR', 'valor': -1000.0}
r = Categorizer().categorizar_lote([t])[0]
assert r['categoria'] == 'Aluguel', f'BUG: {r[\"categoria\"]}'
print('OK pos-fix')
"
```

## Acceptance

- `_verificar_regra_valor` usa `abs(valor)`.
- 4 testes regressivos verdes em `test_categorizer.py`.
- Pytest > 3181, lint exit 0, smoke 10/10.
- Auditoria retroativa documenta N transações que mudaram de categoria.

## Padrões aplicáveis

- (k) Hipótese validada com grep + repro runtime ANTES.
- (s) Specs com "Validação ANTES" obrigatória.
- (cc) Refactor revela teste frágil — auditoria pode pegar outros.

## Arquivos a modificar

- `src/transform/categorizer.py:107-128` (Edit cirúrgico em `_verificar_regra_valor`)
- `tests/test_categorizer.py` (4 testes regressivos novos)
- `data/output/audit_categoria_regra_valor_sinal.json` (gerado, gitignored)

---

*"Sinal de valor é convenção; magnitude é fato." — princípio do comparador honesto*
