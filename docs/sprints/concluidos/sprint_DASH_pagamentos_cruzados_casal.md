---
id: DASH-PAGAMENTOS-CRUZADOS-CASAL
titulo: Dashboard reconhece pagamentos cruzados do casal (Vitória paga boleto do MEI Andre) sem confundir com transferência de terceiro
status: concluida
concluida_em: 2026-05-12
prioridade: P2
data_criacao: 2026-05-12
fase: DASHBOARD
depende_de: []
esforco_estimado_horas: 2
origem: docs/auditorias/VALIDACAO_ARTESANAL_DAS_2026-05-12.md achado colateral -- DAS PARCSN fev/2025 R$ 324,31 do MEI Andre foi pago pela conta Nubank PF da Vitoria; gestao financeira compartilhada do casal. Sem regra explicita, dashboard pode classificar como pagamento por terceiro.  <!-- noqa: accent -->
---

# Sprint DASH-PAGAMENTOS-CRUZADOS-CASAL — reconhecer pagamentos compartilhados

## Contexto

Validação artesanal DAS 2026-05-12 revelou padrão **legítimo** do casal:

- DAS PARCSN fev/2025 (R$ 324,31, MEI do **Andre**) foi pago em 16/04/2025 pela **conta da Vitória** (Nubank PF).
- Tag IRPF: `imposto_pago` (correto).
- Categoria: `Impostos` (correta).
- Quem: pessoa_b (Vitória) — mas o **devedor original** é pessoa_a (Andre, MEI dele).

Sem regra explícita, dashboard pode:
- Confundir esse pagamento com "transferência para terceiro" (saiu da conta da Vitória).
- Falhar em mostrar IRPF de Vitória que ela pagou imposto do Andre (que vai pra dedução de Andre, não dela).
- Não associar corretamente o DAS pago à pessoa que tem a obrigação fiscal.

## Objetivo

1. **Modelo de dados**: adicionar 2 campos opcionais em transações de Impostos:
   - `pessoa_pagadora`: quem pagou (pessoa_a / pessoa_b) — vem do banco origem da transação.
   - `pessoa_devedora`: quem tem a obrigação fiscal — vem do documento (DAS, IRPF, IPVA, etc).
   - Quando `pessoa_pagadora != pessoa_devedora`, é um pagamento cruzado.
2. **Pacote IRPF**:
   - Imposto pago de pessoa_a (mesmo se pessoa_b pagou) entra na declaração de pessoa_a.
   - Dashboard mostra resumo "Pagamentos cruzados do casal" no cluster Análise.
3. **Lógica de match**:
   - Cruzar transação de Imposto com documento (DAS, IPVA, IRPF) via valor + data próxima.
   - Documento tem `cnpj_emitente` ou `cpf` que identifica devedor.
   - Match = pagamento legítimo do casal, não terceiro.
4. **Sentinela**: alerta se >5% dos impostos do mês são pagamentos cruzados sem documento atrelado (pode ser drift de categorização).

## Validação ANTES

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
imp = df[df['categoria']=='Impostos'].copy()
print(f'Total transacoes Impostos: {len(imp)}')
print(f'Pessoa_a (Andre) paga: {len(imp[imp[\"quem\"]==\"pessoa_a\"])}')
print(f'Pessoa_b (Vitoria) paga: {len(imp[imp[\"quem\"]==\"pessoa_b\"])}')
"
sqlite3 data/output/grafo.sqlite "SELECT json_extract(metadata,'\$.cpf_cnpj_devedor'), count(*) FROM node WHERE tipo='documento' AND json_extract(metadata,'\$.tipo_documento') LIKE '%das%' GROUP BY 1"
```

## Não-objetivos

- NÃO criar regra automática que mude `quem` da transação (pessoa_pagadora é dado do banco; intocável).
- NÃO mascarar PII do casal nesta sprint (eles são donos do sistema).
- NÃO renomear transações antigas — só adicionar metadado.
- NÃO incluir outros tipos de pagamentos cruzados (presentes, almoço, etc) — escopo: impostos.

## Critério de aceitação

1. Modelo dados estendido (2 campos opcionais em metadata).
2. Pacote IRPF de pessoa_a inclui DAS R$ 324,31 mesmo pago por pessoa_b (impacto: garantir que essa dedução não seja perdida).
3. Bloco "Pagamentos cruzados do casal" no cluster Análise mostra histórico.
4. Sentinela alerta se >5% impostos sem match.
5. Gauntlet verde.

## Referência

- Auditoria: `docs/auditorias/VALIDACAO_ARTESANAL_DAS_2026-05-12.md`
- Sprint irmã: INFRA-CATEGORIZAR-SALARIO-G4F-C6 (drift de categoria, não cruzado).

*"Casal que paga conta do outro sem pedir explicacao formal eh ouro contabil; sistema que ignora isso fede a tecnocracia." -- principio DASH-PAGAMENTOS-CRUZADOS-CASAL*
