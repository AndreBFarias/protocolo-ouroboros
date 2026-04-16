# Sprint 25 -- Pacote IRPF: Declaração Facilitada

## Status: Pendente

## Objetivo

Gerar toda a papelada necessária para declarar o imposto de renda: organizar documentos por tipo (rendimentos, deduções médicas, impostos pagos), extrair CNPJs dos contrapartes, gerar resumos por categoria, e produzir um pacote pronto para importação ou preenchimento manual.

O IRPF 2026 foi declarado manualmente em 14/04/2026. Esta sprint visa automatizar para os próximos anos.

---

## Entregas

### Organizador de documentos IRPF

- [ ] Criar pasta `data/output/irpf_{ano}/` com subpastas por tipo:
  - `rendimentos/` -- informes de rendimento (G4F, Infobase)
  - `deducoes_medicas/` -- recibos de farmácia, consultas, plano de saúde
  - `impostos/` -- DARFs, DAS MEI, comprovantes de pagamento
  - `isentos/` -- comprovantes de bolsa, FGTS

- [ ] Mover/copiar documentos relevantes de `data/raw/` para as subpastas
  - PDFs de farmácia com CNPJ identificado -> `deducoes_medicas/`
  - Comprovantes de pagamento de imposto -> `impostos/`

### Extração de CNPJ aprimorada

- [ ] Expandir regex para capturar CNPJ de mais fontes:
  - PDFs do Itaú/Santander têm CNPJ do estabelecimento no corpo
  - Nubank CC tem `Identificador` que pode conter CNPJ
  - Notas fiscais (se adicionadas ao inbox) podem ser parseadas

### Resumo IRPF por tipo

- [ ] Gerar `data/output/irpf_{ano}/resumo_irpf.md` com:
  - Total de rendimentos tributáveis (com CNPJ de cada fonte)
  - Total de deduções médicas (com CNPJ de cada profissional/clínica)
  - Total de impostos pagos (DARF, DAS, IRRF retido)
  - Total de rendimentos isentos
  - Checklist do que falta para declaração completa

### Integração com declaração

- [ ] Pesquisar formato do programa IRPF da Receita Federal:
  - Importação via arquivo `.DEC` ou `.DBK`
  - CSV compatível com IRPF
  - Preenchimento automático via e-CAC (API?)

---

## Dados necessários (fontes)

| Dado | Fonte atual | Status |
|------|-------------|--------|
| Rendimentos G4F | Transações bancárias | Parcial (sem CNPJ da G4F) |
| Rendimentos Infobase | Transações bancárias | Parcial (sem CNPJ) |
| Deduções médicas | Tag `dedutivel_medico` | 29 registros, 14 com CNPJ |
| Impostos pagos | Tag `imposto_pago` | 40 registros |
| INSS retido | Contracheque | Sem extrator |
| Informe de rendimentos | PDF do empregador | Sem extrator |

## Armadilhas

- Informe de rendimentos é o documento mais importante e não vem dos extratos bancários -- precisa ser obtido do empregador ou do e-CAC
- Notas fiscais de farmácia nem sempre têm CNPJ legível (impressão térmica)
- DAS MEI de Vitória precisa do CNPJ dela como contribuinte, não do banco

---

*"Na vida, nada deve ser temido, somente compreendido." -- Marie Curie*
