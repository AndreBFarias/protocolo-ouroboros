## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 38
  title: "Fix: Deduplicator fuzzy remove por (data+valor+local) com prioridade anti-histórico"
  touches:
    - path: src/transform/deduplicator.py
      reason: "nível 2 deixa de apenas MARCAR e passa a REMOVER duplicatas; chave inclui local; prioriza banco_origem != Histórico"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_deduplicator.py -x -q"
      timeout: 60
    - cmd: "python -m src.utils.validator"
      timeout: 60
  acceptance_criteria:
    - "Validator reporta 'Sem duplicatas residuais'"
    - "Par legítimo de transferência interna (bancos diferentes) não é removido"
    - "Dedup prefere manter versão com banco_origem != 'Histórico'"
    - "Transferências internas DUPLICADAS na mesma conta (OFX vs CSV) também são removidas"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 38 -- Fix: Deduplicator fuzzy remove por (data+valor+local)

**Status:** CONCLUÍDA
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Bugfix
**Dependências:** Sprint 37 (OFX destravado fez overlap ficar visível)
**Desbloqueia:** Integridade do XLSX consolidado
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint`
- `./run.sh --tudo`
- `python -m src.utils.validator`
- `.venv/bin/pytest tests/test_deduplicator.py -x -q`

### O que NÃO fazer

- NÃO baixar o rigor da dedup (ex: considerar só data+valor) -- risco de remover gastos legítimos
- NÃO remover pares legítimos de Transferência Interna entre bancos diferentes

---

## Problema

Após o fix da Sprint 37, o validator passou a reportar **88 duplicatas residuais** no XLSX consolidado. Inspeção via pandas mostrou dois padrões predominantes:

1. **Histórico vs re-extração atual:** transações importadas do `controle_antigo.xlsx` (banco_origem="Histórico") e as mesmas transações re-extraídas pelo OFX do Nubank (banco_origem="Nubank (PF)") coexistiam no extrato. Ex: `2022-10-20 R$ 16.00 Pag*Pastelarialima` aparecia em ambas fontes.
2. **OFX vs CSV do mesmo banco:** mesma transferência interna listada no OFX e no CSV do mesmo Nubank PF, com idênticos data/valor/local/banco.

A função `deduplicar_por_hash_fuzzy` (src/transform/deduplicator.py:36-73 pré-fix) apenas **marcava** as duplicatas via atributo `_duplicata_fuzzy` mas não removia, com comentário explícito "pode ser coincidência legítima". A chave usada era apenas `(data, valor)`, frouxa demais. Transferências internas eram puladas por segurança, mas isso vazava casos reais de duplicação intra-conta.

Impacto: XLSX consolidado contava duplicatas como se fossem transações distintas, inflando despesas e quebrando relatórios diagnósticos.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Deduplicator 3 níveis | `src/transform/deduplicator.py` | Nível 1 UUID + nível 3 par de TI + nível 2 fuzzy |
| Validator | `src/utils/validator.py:99-116` | Conta duplicatas por (data+valor+local) |
| Pipeline orchestrator | `src/pipeline.py:269` | Chama `deduplicar()` após extração |

---

## Implementação

### Fase 1: chave fuzzy inclui local

Chave passou de `f"{data}|{valor}"` para `f"{data}|{valor}|{local}"`. Alinhada com o validator — o mesmo par é visto por ambos os módulos.

### Fase 2: remove em vez de marcar

Substituição do loop linear por duas passagens:
1. Agrupa índices por chave em `grupos: dict[str, list[int]]`.
2. Para cada grupo com mais de 1 elemento, decide qual índice preservar.

### Fase 3: prioriza banco_origem != "Histórico"

Quando múltiplos índices casam a chave, prefere aquele cuja `banco_origem` NÃO seja "Histórico":

```python
nao_historicos = [i for i in ids if transacoes[i].get("banco_origem") != "Histórico"]
preservar = nao_historicos[0] if nao_historicos else ids[0]
```

Motivo: registros do XLSX antigo têm metadados empobrecidos (sem UUID, sem descrição original completa). A re-extração atual tem dados ricos.

### Fase 4: inclui Transferências Internas

O filtro `if t.get("tipo") == "Transferência Interna": continue` foi removido. Pares LEGÍTIMOS de TI (entre bancos diferentes) não colidem na chave porque o `local` é distinto em cada ponta (ex: "Pix para Vitória" vs "Pix recebido de André").

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A38-1 | Chave de dedup frouxa remove gastos reais coincidentes (dois cafés R$ 5,00 no mesmo dia) | Exigir match também em `local` — coincidência em 3 dimensões é improvável |
| A38-2 | Histórico e re-extração sobrepõem-se silenciosamente | Chave ignora `banco_origem` e prefere-se versão NÃO-histórica na resolução |
| A38-3 | Pares legítimos de TI entre bancos viram "duplicata" | Nível 3 (`marcar_transferencias_internas`) roda ANTES e o `local` distingue as pontas |
| A38-4 | Dedup "marca" sem remover deixa XLSX contaminado | Remove de fato; a decisão binária é mais honesta |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [x] `make lint` passa
- [x] `python -m src.utils.validator` reporta "Sem duplicatas residuais"
- [x] `./run.sh --tudo` consolida 6.136 transações únicas
- [x] Testes de regressão em `tests/test_deduplicator.py` cobrem 9 cenários (OK → ver Sprint 30)
- [x] 88 → 43 → 5 → 0 duplicatas na iteração

---

## Verificação end-to-end

```bash
make lint
./run.sh --tudo
python -m src.utils.validator 2>&1 | grep -E "duplicatas residuais"
# Esperado: "[OK] Sem duplicatas residuais"
.venv/bin/pytest tests/test_deduplicator.py -x -q
```

---

*"O igual reconhece o igual; mas só a diferença ilumina o essencial." -- parafraseando Heráclito*
