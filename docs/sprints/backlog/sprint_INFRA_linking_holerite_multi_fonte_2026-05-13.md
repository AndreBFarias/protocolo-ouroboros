---
id: INFRA-LINKING-HOLERITE-MULTI-FONTE
titulo: Holerite multi-fonte (G4F + INFOBASE) gera conflito artificial no linking
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-13
fase: SANEAMENTO
depende_de: []
esforco_estimado_horas: 3
origem: auditoria pós-./run.sh --tudo em 2026-05-13 -- holerites G4F e INFOBASE (mesma referência 2025-07/2025-12/13o integral) são tratados como documentos separados, e ambos competem pela mesma transação mensal.
---

# Sprint INFRA-LINKING-HOLERITE-MULTI-FONTE

## Contexto

Pessoa_b recebe holerite de DUAS fontes para a mesma competência (G4F + INFOBASE — provavelmente uma é o broker da CLT, outra é a folha). Ambas geram documentos canônicos distintos:

- `HOLERITE|G4F|2025-12` (id 7695)
- `HOLERITE|INFOBASE_-_13o_INTEGRAL|2025-12` (id 7697)

Mas representam o **mesmo evento real**: um depósito mensal na conta. O linker, ao processar os dois, gera 2 propostas conflito separadas — cada uma com 3 candidatas, total 8 conflitos só de holerite no run atual.

## Hipótese arquitetural

Antes de chamar o linker, identificar holerites com (data_emissao, cnpj_emissor distinto) MAS valor_liquido próximo (±5%) — fundir como referências da mesma realidade no grafo (relação `_mesma_realidade_holerite` análogo ao `_eh_mesma_nfce` da sprint INFRA-NFCE-DEDUP-OCR-DUPLICATAS).

Alternativa mais simples: heurística do linker prefere o `nome_canonico` já escolhido para a transação no próximo turn (idempotência inter-execução).

## Proof-of-work esperado

```bash
# Antes do fix: 8 conflitos holerite
# Após fix: <= 2 conflitos holerite (só quando valor_liquido difere mais de 5%)
./run.sh --tudo 2>&1 | grep "conflitos.*holerite" | tail
ls docs/propostas/linking/ | grep -i holerite | wc -l  # deve cair
```

## Padrão canônico aplicável

(hh) Ingestão dupla escapa dedup -- aqui aplicado a documentos, não transações.
(e) PII em 4 sítios -- aplicado à identidade do holerite em 4 sítios distintos do grafo.

---

*"Duas fontes para a mesma realidade não são redundância: são testemunhas." -- princípio da fusão com humildade*
