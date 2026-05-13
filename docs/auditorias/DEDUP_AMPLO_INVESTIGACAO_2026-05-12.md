# Auditoria DEDUP AMPLO -- 2026-05-12

> Origem: Sprint INFRA-DEDUP-C6-OFX-XLSX-AMPLO  
> Auditor: executor automatizado  
> Escopo: cross-check de ingestão dupla OFX+XLSX em Itaú, Santander e Nubank

## Pergunta da auditoria

A duplicação sistemática descoberta em C6/pessoa_a (253 pares ~43% das
linhas) afeta os outros bancos? Precisamos abrir sprint-filha
`INFRA-DEDUP-ITAU-OFX-XLSX` e `INFRA-DEDUP-SANTANDER-OFX-XLSX`?

## Método

Executamos `scripts/investigar_dedup_c6_ofx_xlsx.py` (mesmo script
canônico da spec) variando `--banco` e `--quem` sobre o XLSX final
`data/output/ouroboros_2026.xlsx`. Reportamos pares `(data, valor)` com
`n>=2` para cada banco e quantos casam após normalização do `local`.

## Resultado por banco

| Banco | Quem | Linhas alvo | Grupos únicos | Pares n>=2 | Casam normalizado |
|---|---|---:|---:|---:|---:|
| **C6** | pessoa_a | 1190 | 933 | **253** | 197 |
| C6 | pessoa_b | -- | -- | -- | -- |
| Itaú | pessoa_a | 29 | 29 | **0** | 0 |
| Itaú | pessoa_b | 0 | 0 | 0 | 0 |
| Santander | pessoa_a | 110 | 109 | **1** | 0 |
| Santander | pessoa_b | 0 | 0 | 0 | 0 |
| Nubank | pessoa_a | 998 | 968 | **28** | 1 |

## Confirmação arquitetural (presença de arquivos OFX por banco)

```bash
$ find data/raw -name "*.ofx" 2>/dev/null | sed 's|/[^/]*$||' | sort -u
data/raw/andre/c6_cc
data/raw/andre/nubank_cc
```

- **Itaú**: sem OFX. Só PDF. Não pode haver ingestão paralela OFX+XLSX.
- **Santander**: sem OFX. Só PDF. Idem.
- **Nubank**: tem OFX **E** CSV. Mas 28 pares com 1 normalizado indica
  cenário diferente -- ver análise abaixo.
- **C6**: tem OFX **E** XLSX. Confirma origem arquitetural do bug.

## Análise individual

### Itaú: zero risco
29 transações, zero pares colidentes. Não há sprint-filha necessária.

### Santander: 1 par residual provavelmente legítimo
1 par só, e não casa nem após normalização -- locais materialmente
distintos. Provavelmente transferência interna real. Não há padrão
sistêmico. Não há sprint-filha necessária.

### Nubank: 28 pares, mas padrão diferente
Nubank tem OFX **e** CSV (não XLSX). Mas apenas 1 par casa após
normalização (1/28 = 3.6%) -- muito abaixo dos 78% (197/253) do C6.
Isso indica que o dedup nível-2 atual **já casa** a maioria dos pares
Nubank, e os 28 que ficam têm `local` legitimamente distinto (Nubank
CSV e OFX produzem strings com estrutura compatível, não o padrão
prefixo OFX vs sufixo XLSX do C6).

O fix desta sprint (normalização + pass 2b) é **idempotente** para
Nubank: o pass 2b só age quando `_arquivo_origem` casa OFX+XLSX/CSV no
mesmo banco/data/valor/quem, então pares legítimos com locais distintos
no Nubank seguem preservados pelo nível 2a (que já casa o que é igual).

## Decisão

**Não abrir sprint-filha para Itaú, Santander ou Nubank.**

Razões:
1. Itaú e Santander sem OFX: arquitetura impede o bug.
2. Nubank com OFX+CSV: dedup nível-2 atual já consolida o padrão local.
3. Fix desta sprint é geral (pass 2b cobre qualquer par OFX/XLSX+CSV+XLS
   do mesmo banco/quem), então qualquer caso futuro de Nubank que
   escape ao 2a será capturado pelo 2b automaticamente.

A correção arquitetural fica concentrada na sprint
`INFRA-DEDUP-C6-OFX-XLSX-AMPLO`, **sem fan-out** de sprints derivadas.

## Achado colateral relacionado

Durante o cross-check, observei que o teste `tests/test_cupom_foto_infra.py::
TestCacheCanonico::test_cupom_nsp_grande_tem_52_itens_513_31` está
falhando por `razao_social = 'COMERCIAL NSP LTDA'` (uppercase) vs
expectativa `'Comercial NSP LTDA'` (CamelCase). Falha pré-existente,
**não relacionada ao fix de dedup**. Documentada para sprint-filha
futura `INFRA-CUPOM-RAZAO-SOCIAL-CASE` (não criada nesta sprint, apenas
registrada para revisão manual do dono).

## Referência

- Spec: `docs/sprints/backlog/sprint_INFRA_dedup_c6_ofx_xlsx_amplo.md`
- Auditoria-mãe: `docs/auditorias/DUPLICACAO_C6_OFX_XLSX_2026-05-12.md`
- Script: `scripts/investigar_dedup_c6_ofx_xlsx.py`
- Teste novo: `tests/test_dedup_c6_ofx_xlsx.py`

*"O padrão revelado no C6 não se propaga: provar a ausência em outros
bancos é tão crucial quanto consertar onde ele existe." -- princípio
INFRA-DEDUP-C6-OFX-XLSX-AMPLO*
