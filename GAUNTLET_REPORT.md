# Relatório Gauntlet -- Protocolo Ouroboros

Data: 2026-04-14 19:09:47 | Duração: 0.9s | Python 3.12.1 | Linux

## Resultado Geral: 44/44 (100%)

| Fase | Testes | OK | Falha | Tempo |
|------|--------|----|-------|-------|
| extratores | 2 | 2 | 0 | 0.3s |
| categorias | 16 | 16 | 0 | 0.0s |
| dedup | 4 | 4 | 0 | 0.0s |
| xlsx | 4 | 4 | 0 | 0.0s |
| relatorio | 2 | 2 | 0 | 0.0s |
| projecoes | 4 | 4 | 0 | 0.0s |
| obsidian | 4 | 4 | 0 | 0.0s |
| dashboard | 8 | 8 | 0 | 0.5s |

---

## Detalhes

### Fase: extratores [OK]

- [OK] nubank_cartao: 10 transações extraídas (esperado: 10)
- [OK] nubank_cc: 8 transações extraídas (esperado: 8)

### Fase: categorias [OK]

- [OK] cat.ifood: IFOOD -> Delivery (esperado: Delivery)
- [OK] cat.uber_trip: UBER TRIP -> Transporte (esperado: Transporte)
- [OK] cat.drogaria_raia: DROGARIA RAIA -> Remédios (esperado: Remédios)
- [OK] cat.neoenergia_brasilia: NEOENERGIA BRASILIA -> Energia (esperado: Energia)
- [OK] cat.caesb: CAESB -> Água (esperado: Água)
- [OK] cat.shopee: SHOPEE -> Compras Online (esperado: Compras Online)
- [OK] cat.petz: PETZ -> Pets (esperado: Pets)
- [OK] cat.netflix.com: NETFLIX.COM -> Assinaturas (esperado: Assinaturas)
- [OK] cat.mercado_livre: MERCADO LIVRE -> Compras Online (esperado: Compras Online)
- [OK] cat.sesc_natacao: SESC NATACAO -> Educação e Esporte (esperado: Educação e Esporte)
- [OK] cls.ifood: IFOOD -> classificação: Questionável (esperado: Questionável)
- [OK] cls.neoenergia_brasilia: NEOENERGIA BRASILIA -> classificação: Obrigatório (esperado: Obrigatório)
- [OK] cls.shopee: SHOPEE -> classificação: Supérfluo (esperado: Supérfluo)
- [OK] cls.drogaria_raia: DROGARIA RAIA -> classificação: Obrigatório (esperado: Obrigatório)
- [OK] cls.petz: PETZ -> classificação: Obrigatório (esperado: Obrigatório)
- [OK] fallback_outros: Desconhecido -> Outros (esperado: Outros)

### Fase: dedup [OK]

- [OK] dedup_l1_uuid: 3 restantes (esperado: 3)
- [OK] dedup_l2_fuzzy: 3 mantidas, 1 marcadas como fuzzy (esperado: 3 mantidas, 1 marcada)
- [OK] dedup_l3_transferencia: 2 transferências internas (esperado: 2)
- [OK] dedup_pipeline_completo: 3 finais (esperado: 3)

### Fase: xlsx [OK]

- [OK] gerar_xlsx: XLSX gerado sem erros
- [OK] abas_existem: 8 abas encontradas: extrato, renda, dividas_ativas, inventario, prazos, resumo_mensal, irpf, analise
- [OK] colunas_extrato: Colunas OK: 12
- [OK] contagem_linhas: 10 linhas (esperado: 10)

### Fase: relatorio [OK]

- [OK] geracao_relatorio: Relatório gerado: 1908 caracteres
- [OK] secoes_obrigatorias: Todas as 5 seções presentes

### Fase: projecoes [OK]

- [OK] medias_mensais: Receita: 18700.00 (esperado: 18700.00), Despesa: 8000.00 (esperado: 8000.00), Saldo: 10700.00 (esperado: 10700.00)
- [OK] meses_ate_objetivo: R$ 5k/mês até R$ 27k: 6 meses (esperado: 6), Saldo negativo: None (esperado: None), Já atingido: 0 (esperado: 0)
- [OK] projecao_acumulada: 12 pontos, mês 1: 15000 (esperado: 15000), mês 12: 70000 (esperado: 70000)
- [OK] cenarios_completos: Cenários: atual=True, pós=True, apê=True. Saldo atual: 10700.00, Pós-Infobase: 3258.00

### Fase: obsidian [OK]

- [OK] sync_relatorios: 1 relatórios sincronizados, arquivo existe: True
- [OK] frontmatter: Frontmatter OK
- [OK] notas_metas: 3 notas de metas criadas (esperado: 3)
- [OK] idempotencia: Idempotente (ignorando created)

### Fase: dashboard [OK]

- [OK] import.app: src.dashboard.app importado com sucesso
- [OK] import.dados: dados importado, formatar_moeda: True
- [OK] import.visao_geral: src.dashboard.paginas.visao_geral importado com sucesso
- [OK] import.categorias: src.dashboard.paginas.categorias importado com sucesso
- [OK] import.extrato: src.dashboard.paginas.extrato importado com sucesso
- [OK] import.contas: src.dashboard.paginas.contas importado com sucesso
- [OK] import.projecoes: src.dashboard.paginas.projecoes importado com sucesso
- [OK] import.metas: src.dashboard.paginas.metas importado com sucesso

---

*"Medir é saber. Não medir é adivinhar." -- Lord Kelvin*
