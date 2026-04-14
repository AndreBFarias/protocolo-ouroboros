# CONTEXTO.md -- Quem somos e por que este projeto existe

## O Casal

**André** -- Analista/Engenheiro de Dados. Trabalha no MEC via G4F (contrato federal). Antes Infobase. Usa Itaú (CC, agência 6450), Santander (cartão Elite Visa final 7342), C6 (CC + cartão), Nubank (cartão).

**Vitória** -- Bolsista NEES/UFAL (R$ 3.700/mês, isento de IR). Usa Nubank PF (conta 97737068-1) e Nubank PJ (CNPJ 52.488.753, conta 96470242-3). Tem duas dívidas Nubank em caducidade (PF R$ 13.049 + PJ R$ 10.783).

## O Problema

Antes deste projeto, as finanças do casal estavam espalhadas em:
- 7+ fontes bancárias (CSVs, XLSX, XLS encriptados, PDFs protegidos, screenshots)
- Uma planilha manual com 1.254 lançamentos (ago/2022 a jul/2023)
- Nenhuma visão consolidada de receita vs despesa
- Nenhuma categorização automática
- Nenhum controle de IRPF
- Um vault Obsidian em ~/Controle de Bordo/ com documentos pessoais, profissionais e acadêmicos desorganizados

## A Solução

Pipeline ETL financeiro pessoal que:
1. **Lê** arquivos brutos de qualquer formato (detecta banco/tipo/pessoa pelo conteúdo)
2. **Extrai** transações padronizadas
3. **Deduplica** entre fontes (3 níveis: UUID, hash, pares de transferência)
4. **Categoriza** automaticamente (111 regras regex + 10 overrides manuais = 100% cobertura)
5. **Tageia** para IRPF (21 regras, 5 tipos fiscais)
6. **Gera** XLSX consolidado com 8 abas + 44 relatórios mensais em Markdown
7. **Apresenta** via dashboard Streamlit com 6 páginas interativas
8. **Sincroniza** com vault Obsidian

## Números Atuais

- **2.859 transações** processadas (1.214 histórico + 1.645 dados brutos)
- **44 meses** de cobertura (ago/2022 a out/2026)
- **6 bancos** suportados (Itaú, Santander, C6, Nubank PF, Nubank PJ, Neoenergia OCR)
- **111 regras regex** + **10 overrides** = 100% categorização
- **79 registros IRPF** tagueados automaticamente
- **6.889 linhas** de código Python em 38 arquivos

## Visão de Futuro

O projeto vai se tornar o **novo Controle de Bordo** -- centralizando não apenas finanças, mas toda a vida do casal:
- Documentos pessoais (contratos, diplomas, currículos)
- Vida acadêmica (disciplinas, certificados)
- Vida profissional (holerites, registrato BCB)
- Metas financeiras (reserva de emergência, apartamento, CNH)
- Integração com celular via Obsidian mobile
- Análise financeira via LLM local (Gemma/Phi na RTX 3050)

## Estado do Projeto

4 sprints concluídas e validadas. 2 sprints com código integrado mas validação pendente. 8 sprints futuras documentadas. Issues #3, #5, #6 reabertas para validação profunda.

Para começar a trabalhar, leia `CLAUDE.md` e `GSD.md`.

---

*"Conhece-te a ti mesmo." -- Sócrates*
