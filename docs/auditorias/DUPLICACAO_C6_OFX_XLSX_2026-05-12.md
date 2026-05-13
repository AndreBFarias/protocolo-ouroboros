# Auditoria DUPLICACAO_C6_OFX_XLSX -- 2026-05-12

> Origem: Sprint INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F  
> Auditor: executor automatizado + revisão do dono pendente  
> Escopo: lançamentos C6 / pessoa_a no XLSX `ouroboros_2026.xlsx`

## Diagnóstico

O par sinalizado (`2026-03-06 / R$ 6.381,14 / C6 / pessoa_a`) **não é uma
duplicação isolada**: é manifestação de um **padrão arquitetural amplo de
ingestão dupla** das mesmas transações C6, originadas por dois extratores
paralelos:

1. **`src/extractors/ofx_parser.py`** -- lê `BANCARIO_C6_OFX_*.ofx`.
   Compõe `descricao = t_ofx.memo or t_ofx.payee`, gerando strings  <!-- noqa-acento -->
   prefixadas (`"RECEBIMENTO SALARIO - <NOME-CONTA>"`,
   `"DEBITO DE CARTAO - <ESTABELECIMENTO>"`,
   `"PGTO FAT CARTAO C6 - Fatura de cartão"`, etc.).
2. **`src/extractors/c6_cc.py`** -- lê `BANCARIO_C6_CC_*.xlsx`.
   Compõe `descricao_completa = "<titulo> - <descricao>"` ou apenas  <!-- noqa-acento -->
   `<titulo>`, gerando strings **sem o prefixo bancário** (`"<NOME-CONTA>"`,
   `"<ESTABELECIMENTO>          <CIDADE>      BRA"`,
   `"Fatura de cartão"`, etc.).

Ambos os extratores rodam no mesmo `make run`, escrevendo no XLSX final
sem que `src/transform/deduplicator.py::deduplicar_por_hash_fuzzy` consiga
casar pelo trio `(data, valor, local)` -- porque o campo `local`, derivado
de `descricao` via `extrair_local`, **fica diferente em cada origem**.  <!-- noqa-acento -->

### Evidência empírica (2026-05-12)

Output de `scripts/investigar_dedup_c6_ofx_xlsx.py`:

```
Linhas alvo (C6/pessoa_a): 1190
Grupos unicos (data, valor): 933
Pares suspeitos (n>=2):       253
Casam apos normalizar local:  197
```

CSV bruto preservado em `/tmp/dedup_c6_ofx_xlsx_1778634895.csv` (não vai
para repo por ser dado pessoal). 253 pares (~510 linhas, 43% do total
C6/pessoa_a) têm `(data, valor)` colidente; 197 deles passam a casar
quando se normaliza o `local` removendo tudo antes do separador ` - `.

### Caso específico da spec

```
id  | data       | valor   | forma   | local
7143| 2026-03-06 | 6381.14 | Crédito | 5127373122-ANDRE DA SILVA BATISTA DE FAR
7146| 2026-03-06 | 6381.14 | Débito  | RECEBIMENTO SALARIO - 5127373122-ANDRE DA SILVA BATISTA DE F
```

Ambos correspondem ao **mesmo crédito de salário G4F** (R$ 6.381,14) na
conta corrente C6. Não é "duplicação de importação do mesmo arquivo"; é o
mesmo lançamento bancário lido pelo OFX (id 7146, com prefixo
`RECEBIMENTO SALARIO -`) e pelo XLSX (id 7143, sem prefixo, com truncamento
para 39 chars `...FAR` vs `...F`).

A divergência de `forma_pagamento` (Débito vs Crédito) reflete que o
extrator OFX e o XLSX inferem campos diferentes a partir das mesmas
linhas -- com regras heurísticas distintas em
`ofx_parser.py::_inferir_forma_pagamento` versus
`c6_cc.py::_inferir_forma_pagamento`.

## Causa raiz

Ingestão paralela com **dedup nível-2 cego ao prefixo bancário**:

```python
# src/transform/deduplicator.py::deduplicar_por_hash_fuzzy
chave = f"{data_str}|{valor_str}|{local}"  # local = sufixo não normalizado
```

Como o `local` do XLSX é tipicamente sufixo do `local` do OFX (após o
primeiro ` - `), a chave nunca coincide e o dedup falha silenciosamente.

## Decisão da sprint INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F

A spec atual declara "Não-objetivos: NÃO incluir outras duplicatas
potenciais nesta sprint (escopo: só essa)". O achado refuta a hipótese
de "caso isolado": são 253 pares estruturais.

Aplicar UPDATE retroativo só no par dado deixaria os outros 252
inconsistentes e seria volátil (próximo `make run` reinsere). Aplicar fix
arquitetural amplo (normalização de `local` no dedup nível-2 ou eliminação
de uma das fontes) excederia o escopo desta sprint.

**Decisão**: documentar diagnóstico aqui, escalar para sprint-filha
`INFRA-DEDUP-C6-OFX-XLSX-AMPLO`, **não** mexer no grafo nem no XLSX agora.

## Próximas ações (sprint-filha)

Ver `docs/sprints/backlog/sprint_INFRA_dedup_c6_ofx_xlsx_amplo.md`.

Opções arquiteturais a avaliar:

1. **Eliminação de uma fonte**: deixar apenas `c6_cc.py` (XLSX é mais
   confiável para C6 conforme histórico). Drop `BANCARIO_C6_OFX_*.ofx` da
   ingestão automática ou rotear para `data/raw/_arquivado/`.
2. **Fingerprint normalizado no dedup nível-2**: normalizar `local`
   removendo prefixos bancários conhecidos (`"RECEBIMENTO SALARIO -"`,
   `"DEBITO DE CARTAO -"`, `"PGTO FAT CARTAO C6 -"`, etc.) ou aplicar
   regra geral "sufixo após primeiro ` - `". Risco: falso positivo em
   pares legítimos (ex.: duas transferências do casal no mesmo dia com
   mesmo valor mas destinatários diferentes).
3. **Precedência explícita por `arquivo_origem`**: quando `(data, valor,
   sufixo_normalizado)` colide, preservar OFX (mais bruto) e descartar
   XLSX, ou vice-versa.

Recomenda-se opção (1) como menos arriscada.

## Referência

- Spec mãe: `docs/sprints/concluidos/sprint_INFRA_dedup_lancamento_duplicado_g4f.md`
- Sprint-filha: `docs/sprints/backlog/sprint_INFRA_dedup_c6_ofx_xlsx_amplo.md`
- Script de investigação: `scripts/investigar_dedup_c6_ofx_xlsx.py`
- Teste regressivo (documenta cenário e valida normalização proposta):
  `tests/test_dedup_lancamento.py`
- Sprint irmã: `INFRA-CATEGORIZAR-SALARIO-G4F-C6` (categoria errada do
  mesmo lançamento, em execução paralela em outro worktree)
- Auditoria geradora: `docs/auditorias/VALIDACAO_ARTESANAL_HOLERITE_2026-05-12.md`
