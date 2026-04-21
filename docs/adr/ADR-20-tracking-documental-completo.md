# ADR-20 — Tracking documental: todo pagamento tem comprovante rastreável

**Status:** PROPOSTO
**Data:** 2026-04-21

## Contexto

Andre declarou a visão: "quando eu clicar em Natação André, quero ver o boleto E o recibo". Hoje o grafo tem 2 documentos catalogados (Sprint 57 expôs); 99% das transações não têm comprovante vinculado. Isso é o coração do projeto.

Motivação real: fiscalização interna de gastos (toda assinatura de farmácia psiquiátrica documentada, declara IRPF, deduz imposto), pressão para questionar cada ifood ("tenho recibo? pq essa comida é de R$ 85?"), provar aluguel (padaria Ki-Sabor R$ 800-900 = aluguel).

## Decisão

**Toda transação vira "aberta" até ter pelo menos um documento vinculado. A completude documental é um KPI de primeira linha.**

### Regras

1. **Tipos de vínculo no grafo:**
   - `documento -> pago_com -> transacao` (canônico, já existe — Sprint 48 estava incompleta)
   - `documento -> confirma -> transacao` (boleto oficial emitido pela empresa)
   - `documento -> comprovante -> transacao` (recibo/cupom/voucher do momento do pagamento)
   - `documento -> origem -> transacao` (contrato/fatura que originou a cobrança recorrente — ex: Energisa mensal)

2. **Estados de transação:**
   - `aberta` — sem vínculo
   - `confirmada` — tem `confirma` OU `comprovante`
   - `totalmente_documentada` — tem `origem` + `confirma` + `comprovante`
   - `irrecuperavel` — supervisor marcou explicitamente que o documento original não existe mais (ex: boletos antigos removidos do site do fornecedor, faturas não arquivadas). Contagem separada no gap analysis — não pesa como pendência ativa.

3. **Categorias com tracking obrigatório** (definidas via `mappings/categorias_tracking.yaml`):
   - Farmácia (para IRPF)
   - Saúde (para IRPF)
   - Aluguel (para comprovação de moradia)
   - Educação (para IRPF)
   - Impostos (obrigatório por lei)
   - Outras marcadas como `obrigatoria_tracking: true`

4. **Dashboard mostra completude por categoria obrigatória:**
   - "Farmácia 2026: 0/37 comprovantes — R$ 2.840 sem recibo"
   - "Aluguel 2026: 4/4 OK" (se padaria Ki-Sabor está vinculada aos 4 pagamentos)

5. **Nota Obsidian gerada** para cada documento, em `~/Controle de Bordo/Pessoal/Casal/Financeiro/Documentos/{YYYY-MM}/{slug}.md`, com frontmatter:
   ```yaml
   tipo: documento
   documento_id: 12345
   transacao_id: [67890, 67891]  # lista (um doc pode cobrir várias transações)
   data: 2026-04-15
   fornecedor: "[[Neoenergia]]"
   categoria: "[[Energia]]"
   arquivo_original: "[[_Attachments/neoenergia_202604_boleto.pdf]]"
   valor: 432.90
   tipo_documento: boleto
   estado: confirmada
   ```

6. **Matching automático** (heurística):
   - Data do documento +- 3 dias da transação
   - Valor exato
   - Fornecedor (via entity resolution Sprint 49)
   - Score >0.8 -> vínculo auto; 0.5-0.8 -> proposta supervisor em `docs/propostas/linking/`; <0.5 -> nada.

7. **Fallback manual:** modal da transação (Sprint 74) tem botão "Associar documento" que lista arquivos na inbox ainda não vinculados.

## Consequências

### Positivas
- Pacote IRPF vira automático (Sprint 25): script coleta todos os `documento_de_irpf_dedutivel` do ano e empacota.
- Auditoria interna: "Quanto gastei com farmácia em 2024?" lista + comprovantes em 1 clique.
- Andre consegue negociar descontos mostrando histórico: "pago R$ 500/mês há 24 meses, posso ter desconto?".

### Custos
- Sprint 74 + 75 carregam peso desta decisão.
- Usuário precisa jogar comprovante na inbox com disciplina (workflow Sprint 80 reduz fricção).
- Grafo cresce rápido (estimado +30 nodes por mês se Andre documentar de verdade).

## Sprints desbloqueadas

- **Sprint 74** — Vinculação transação <-> documento (motor de matching + modal)
- **Sprint 75** — Gap analysis (lista o que falta)
- **Sprint 79** — Tracking de boletos / pix / crédito (visão por forma de pagamento)

---

*"Documento perdido é dívida futura." — princípio de higiene financeira*
