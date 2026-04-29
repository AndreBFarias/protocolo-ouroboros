---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: INFRA-parse-br
  title: "Extrair _parse_valor_br duplicado em 8 extratores para src/utils/parse_br.py"
  touches:
    - path: src/utils/parse_br.py
      reason: "novo: função canônica parse_valor_br(str | None) -> float | None"
    - path: src/extractors/itau_pdf.py
      reason: "remover redefinição local, importar de src.utils.parse_br"
    - path: src/extractors/santander_pdf.py
    - path: src/extractors/contracheque_pdf.py
    - path: src/extractors/cupom_garantia_estendida_pdf.py
    - path: src/extractors/danfe_pdf.py
    - path: src/extractors/nfce_pdf.py
    - path: src/extractors/cupom_termico_foto.py
    - path: src/extractors/boleto_pdf.py
    - path: tests/test_utils_parse_br.py
      reason: "4-5 testes da função consolidada: formatos canônicos, None, inválido, exceção"
  n_to_n_pairs:
    - ["_parse_valor_br redefinido local nos 8 extratores", "import único de src.utils.parse_br"]
  forbidden:
    - "Alterar o comportamento da função: contrato é idêntico nos 8 redefinidos hoje"
    - "Remover a citação filosófica do fim de qualquer .py tocado"
    - "Tocar extratores que não têm _parse_valor_br local (recibo_nao_fiscal, receita_medica, garantia)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "src/utils/parse_br.py::parse_valor_br existe e tem docstring canônica"
    - "Os 8 extratores importam de src.utils.parse_br em vez de redefinir"
    - "Aritmética: ~55 linhas removidas (8 × ~7L de definição local)"
    - "Zero mudança comportamental: todos os testes de extrator continuam passando"
    - "tests/test_utils_parse_br.py com 4+ testes cobrindo: 1.234,56 -> 1234.56, 103,93 -> 103.93, None -> None, 'abc' -> None"
    - "Baseline de testes cresce ou mantém (+4 testes do novo módulo)"
  proof_of_work_esperado: |
    # Aritmética explícita
    wc -l src/extractors/*.py | grep _parse_valor_br   # antes
    grep -l "_parse_valor_br" src/extractors/*.py | wc -l  # deve ir para 0 após refactor
    grep -l "from src.utils.parse_br import parse_valor_br" src/extractors/*.py | wc -l  # ~8
    # Gauntlet
    make lint && .venv/bin/pytest tests/ -q && make smoke
```

---

# Sprint INFRA-parse-br — Consolidar `_parse_valor_br` em utils

**Status:** BACKLOG INFRA
**Prioridade:** BAIXA (não-bloqueante; valor do projeto é higiene + DRY)
**Dependências:** Sprint 87.3 (acrescentou o 8º redefinidor: `boleto_pdf.py`)
**Origem:** BRIEF §91 (padrão recorrente) confirmado novamente em Sprint 87.3

## Problema

8 extratores redefinem localmente a mesma função `_parse_valor_br(str | None) -> float | None`:

```python
def _parse_valor_br(valor_str: str | None) -> float | None:
    if valor_str is None:
        return None
    limpo = valor_str.replace(".", "").replace(",", ".").strip()
    try:
        return float(limpo)
    except (ValueError, TypeError):
        return None
```

Localizações confirmadas (BRIEF §91 + auditoria pós-87.3):

| Arquivo | Linha aprox. |
|---|---|
| `src/extractors/itau_pdf.py` | 207 |
| `src/extractors/santander_pdf.py` | 357 |
| `src/extractors/contracheque_pdf.py` | 55 |
| `src/extractors/cupom_garantia_estendida_pdf.py` | 513 |
| `src/extractors/danfe_pdf.py` | 572 |
| `src/extractors/nfce_pdf.py` | 539 |
| `src/extractors/cupom_termico_foto.py` | 296 |
| `src/extractors/boleto_pdf.py` | 205 (**novo — Sprint 87.3**) |

A função é IDÊNTICA em todos. Não há especialização. Refactor puro para `src/utils/parse_br.py` é seguro e elimina débito.

## Escopo

### INFRA-parse-br.1 — Criar `src/utils/parse_br.py`

```python
"""Parser canônico de valores em formato brasileiro (R$ 1.234,56 → 1234.56)."""

from __future__ import annotations


def parse_valor_br(valor_str: str | None) -> float | None:
    """Converte string no formato 'X.XXX,YY' (BR) em float. None em entrada inválida.

    Exemplos:
        parse_valor_br("1.234,56") -> 1234.56
        parse_valor_br("103,93") -> 103.93
        parse_valor_br(None) -> None
        parse_valor_br("abc") -> None
        parse_valor_br("") -> None

    Função consolidada da Sprint INFRA-parse-br. 8 extratores redefiniam
    localmente até então (BRIEF §91). Contrato preservado: troca
    transparente para quem importa.
    """
    if valor_str is None:
        return None
    limpo = valor_str.replace(".", "").replace(",", ".").strip()
    if not limpo:
        return None
    try:
        return float(limpo)
    except (ValueError, TypeError):
        return None


# "A simplicidade é a elegância final da repetição." -- princípio DRY
```

### INFRA-parse-br.2 — Substituir nos 8 extratores

Em cada arquivo: remover a função `_parse_valor_br` local, substituir chamadas por `parse_valor_br`, adicionar `from src.utils.parse_br import parse_valor_br` no topo. Use MultiEdit com padrão bem definido. Validar arquivo por arquivo com `pytest tests/test_<extrator>.py -q`.

### INFRA-parse-br.3 — Testes canônicos

`tests/test_utils_parse_br.py`:

```python
import pytest
from src.utils.parse_br import parse_valor_br


def test_parse_valor_br_formato_com_milhar():
    assert parse_valor_br("1.234,56") == pytest.approx(1234.56)


def test_parse_valor_br_formato_simples():
    assert parse_valor_br("103,93") == pytest.approx(103.93)


def test_parse_valor_br_none_entra_none_sai():
    assert parse_valor_br(None) is None


def test_parse_valor_br_invalido_vira_none():
    assert parse_valor_br("abc") is None


def test_parse_valor_br_vazio_vira_none():
    assert parse_valor_br("") is None
    assert parse_valor_br("   ") is None


def test_parse_valor_br_com_simbolo_r_cifrao():
    # padrão R$ 127,00 → strip externo, função interna NÃO remove R$, é só o valor numerico
    # Se o caller passa "R$ 127,00", retorno é None (não é responsabilidade parsear prefixo)
    assert parse_valor_br("R$ 127,00") is None
```

### INFRA-parse-br.4 — Aritmética de verificação

Rodar e incluir no proof-of-work:

```bash
# antes (referência)
grep -c "^def _parse_valor_br" src/extractors/*.py
# deve somar 8 (ou a contagem atual; confirmar no início da sprint)

# depois
grep -c "^def _parse_valor_br" src/extractors/*.py
# deve dar 0

grep -l "from src.utils.parse_br import parse_valor_br" src/extractors/*.py | wc -l
# deve dar 8

wc -l src/extractors/*.py | grep total  # total de linhas deve cair ~55
```

## Armadilhas

- O comportamento precisa ser BIT-A-BIT idêntico. Se algum extrator tiver `strip()` adicional ou tratamento especial (ex: prefixo `R$`), NÃO generalizar no helper — use wrapper local só no extrator que precisa. Confirme lendo cada definição antes de refatorar.
- Rename de `_parse_valor_br` (com underline) para `parse_valor_br` (sem) é necessário porque a nova é pública. Mas isso muda o nome em todos os call-sites. Use MultiEdit com cuidado — não substituir em comentários/docstrings que citam a versão antiga.
- Testes específicos de extrator cobrem a função indiretamente (ex: `test_itau_pdf::test_extrai_valor_X`). Eles DEVEM continuar passando. Qualquer quebra sinaliza divergência comportamental que precisa ser investigada.
- BRIEF §91 já registra essa sprint como candidata INFRA; o validador não reprova projetos que redefinem localmente — isso é opcional higiene.

## Evidência obrigatória

- [ ] `src/utils/parse_br.py` existe com 1 função pública + docstring + citação
- [ ] 8 extratores importam da utils; 0 redefinem
- [ ] 5+ testes em `tests/test_utils_parse_br.py` cobrindo casos canônicos
- [ ] Todos os testes de extrator existentes continuam verdes
- [ ] Aritmética de linhas: ~55L removidas do src/extractors/
- [ ] Gauntlet verde

---

*"O que se repete 8 vezes merece um nome só." — princípio DRY aplicado ao tempo*
