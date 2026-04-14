# ADR-02: XLSX como formato de saída principal

## Status: Aceita

## Contexto

O usuário já controlava finanças em planilha Excel com múltiplas abas. O formato de saída precisava ser facilmente acessível, editável manualmente quando necessário, e portável (funciona em qualquer máquina com leitor de planilha).

Alternativas consideradas:
- **SQLite**: queries poderosas, mas exige ferramenta extra para visualizar. Usuário não tem familiaridade com SQL.
- **CSV**: simples, mas não suporta múltiplas abas. Perderia a estrutura organizacional.
- **Parquet**: ótimo para análise, mas ilegível sem ferramentas especializadas.

## Decisão

Manter XLSX como formato principal de saída, gerado via openpyxl. O arquivo contém 8 abas (extrato, renda, dividas_ativas, inventario, prazos, resumo_mensal, irpf, analise), cada uma com schema definido e formatação de colunas.

O XLSX funciona como "banco de dados flat" -- sem relações formais, mas com convenções de chave (mes_ref) que permitem cruzamento entre abas.

## Consequências

**Positivas:**
- Abre em Excel, LibreOffice, Google Sheets sem configuração
- Usuário pode editar manualmente e o pipeline preserva edições (overrides.yaml)
- Portável: arquivo único contém todo o histórico financeiro
- Múltiplas abas mantêm organização lógica sem fragmentar em arquivos

**Negativas:**
- Sem queries SQL: análises complexas exigem pandas ou filtros manuais
- Limite prático de ~1M linhas por aba (irrelevante para uso pessoal)
- Merge de alterações manuais e programáticas requer cuidado (overrides.yaml resolve parcialmente)
- Formatação condicional e fórmulas não são geradas pelo pipeline (apenas dados)

---

*"Simplicidade é a sofisticação suprema." -- Leonardo da Vinci*
