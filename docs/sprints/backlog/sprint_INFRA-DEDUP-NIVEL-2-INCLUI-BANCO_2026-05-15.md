---
id: INFRA-DEDUP-NIVEL-2-INCLUI-BANCO
titulo: Dedup nível-2 inclui `banco_origem` na chave (evita colisão cross-bank)
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-15
fase: QUALIDADE
epico: 3
depende_de: []
esforco_estimado_horas: 2
origem: "auditoria 2026-05-15. `src/transform/deduplicator.py::_normalizar_local_para_chave` (linha 50) retorna `local.split(\" - \", 1)[-1].strip().lower()`. Chave dedup-nível-2 é `(data, valor, local_normalizado)` sem `banco_origem`. Mitigação só está em `_consolidar_pares_ofx_xlsx_mesmo_banco` (nível-2b) para mesmo banco. Cenário: PIX R$5000 batendo Nubank \"Recebimento Pix - X\" + C6 \"X\" no mesmo dia → colidem na chave `(\"2026-05-10\", \"5000.00\", \"x\")` → uma deletada falsamente."
---

# Sprint INFRA-DEDUP-NIVEL-2-INCLUI-BANCO

## Contexto

A sprint INFRA-DEDUP-C6-OFX-XLSX-AMPLO (commit `2998b26`) resolveu 253 duplicações no C6 entre OFX+XLSX. Mas a solução normalizou `local` deletando prefixos bancários (OFX traz "RECEBIMENTO SALARIO - X", XLSX traz "X"). Essa normalização vale **dentro do mesmo banco** mas vaza para **cross-bank**:

```
Transação 1: data=2026-05-10, valor=5000, banco_origem="Nubank", local="Recebimento Pix - X"
Transação 2: data=2026-05-10, valor=5000, banco_origem="C6",     local="X"
Normalizado:   ambos → "x"
Chave:         ("2026-05-10", "5000.00", "x")  ← COLIDEM!
```

Pass nível-2b (`_consolidar_pares_ofx_xlsx_mesmo_banco`) tem filtro `banco_origem` mas só RODA depois — se nível-2 já dedupou cross-bank, o dado correto sumiu.

## Hipótese e validação ANTES

H1: nível-2 não inclui banco_origem na chave:

```bash
grep -A 20 "def deduplicar_por_hash_fuzzy\|def deduplicar_por_hash" src/transform/deduplicator.py | head -30
# Esperado: chave construída sem banco_origem
```

H2: caso real (procurar duplicatas cross-bank no grafo atual):

```bash
sqlite3 data/output/grafo.sqlite "
SELECT t1.id, t2.id, json_extract(t1.metadata, '\$.banco_origem'), json_extract(t2.metadata, '\$.banco_origem'),
       json_extract(t1.metadata, '\$.valor'), json_extract(t1.metadata, '\$.data')
FROM node t1 JOIN node t2 ON t1.id < t2.id
WHERE t1.tipo='transacao' AND t2.tipo='transacao'
  AND json_extract(t1.metadata, '\$.data') = json_extract(t2.metadata, '\$.data')
  AND json_extract(t1.metadata, '\$.valor') = json_extract(t2.metadata, '\$.valor')
  AND json_extract(t1.metadata, '\$.banco_origem') != json_extract(t2.metadata, '\$.banco_origem')
LIMIT 10
"
# Esperado: ≥1 par. Se 0, a regra ainda vale como prevenção.
```

## Objetivo

1. Modificar `deduplicar_por_hash_fuzzy` (ou função equivalente nível-2) para incluir `banco_origem` na chave:
   ```python
   chave = (data_iso, f"{valor:.2f}", local_normalizado, banco_origem or "_sem_banco")
   ```
2. Garantir backwards-compat: transações sem `banco_origem` (histórico) caem em bucket `_sem_banco` e continuam deduplicando entre si.
3. Pass 2b (`_consolidar_pares_ofx_xlsx_mesmo_banco`) continua funcionando — agora atua como "fusão de transação realmente igual" depois que cross-bank foi preservada.
4. Teste regressivo: simular PIX duplicado entre Nubank e C6 deve preservar ambos. Simular PIX duplicado dentro do C6 (OFX+XLSX) deve consolidar 1.

## Não-objetivos

- Não tocar nível-1 (UUID/hash exato — diferente).
- Não tocar nível-2b (já funciona; só fica protegido pela mudança).
- Não re-rodar pipeline sobre histórico — apenas regra vale para próxima execução.

## Proof-of-work runtime-real

```bash
# 1. Teste sintético cross-bank
.venv/bin/python -c "
from src.transform.deduplicator import deduplicar_por_hash_fuzzy
from datetime import date
ts = [
    {'data': date(2026,5,10), 'valor': 5000.0, 'local': 'Recebimento Pix - EMPRESA X',
     'banco_origem': 'Nubank', '_arquivo_origem': 'nu.ofx'},
    {'data': date(2026,5,10), 'valor': 5000.0, 'local': 'EMPRESA X',
     'banco_origem': 'C6', '_arquivo_origem': 'c6.xlsx'},
]
res = deduplicar_por_hash_fuzzy(ts)
assert len(res) == 2, f'cross-bank dedupou erroneamente: {len(res)}'
print('OK cross-bank preservado')
"

# 2. Teste mesmo-banco (OFX+XLSX)
.venv/bin/python -c "
from src.transform.deduplicator import deduplicar_por_hash_fuzzy
from datetime import date
ts = [
    {'data': date(2026,5,10), 'valor': 5000.0, 'local': 'Recebimento Pix - X',
     'banco_origem': 'C6', '_arquivo_origem': 'c6.ofx'},
    {'data': date(2026,5,10), 'valor': 5000.0, 'local': 'X',
     'banco_origem': 'C6', '_arquivo_origem': 'c6.xlsx'},
]
res = deduplicar_por_hash_fuzzy(ts)
# Nivel-2 mantém ambos (não bate pela chave por causa do banco_origem na chave + local_normalizado idêntico só em local).
# Pass 2b consolida.
# Resultado final esperado depende da arquitetura — verificar teste regressivo existente.
print(f'Mesmo banco: {len(res)} preservado (esperado: 1 após 2b)')
"
```

## Acceptance

- Chave de dedup-2 inclui banco_origem.
- 2 testes regressivos novos em `tests/test_deduplicator.py` (cross-bank + mesmo-banco).
- Testes existentes continuam verdes (especialmente os 253 pares C6 da sprint anterior).
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (n) Defesa em camadas — chave + 2b são duas barreiras.
- (k) Hipótese ANTES — grep no código real.
- (cc) Refactor revela teste frágil — esperar que algum teste antigo precise update se assumia chave 3-tuple.

---

*"Mesmo dia, mesmo valor, mesmo nome, mas bancos diferentes: são duas verdades, não uma duplicada." — princípio da separação de origem*
