# ADR-07: Princípio Local First

## Status: Aceita

## Contexto

Dados financeiros pessoais são altamente sensíveis: extratos bancários, valores de salário, CPF, padrões de consumo. Qualquer dependência de serviços cloud introduz riscos de privacidade, custos recorrentes e pontos de falha.

O pipeline precisa funcionar em ambiente doméstico, sem internet, sem assinaturas, sem contas em serviços terceiros.

## Decisão

Tudo funciona offline por padrão:

- **Processamento**: Python local, sem chamadas a APIs externas
- **OCR**: tesseract-ocr local (não Google Vision ou AWS Textract)
- **Categorização**: regex determinístico local (não LLM via API)
- **Armazenamento**: XLSX em disco local, sem banco de dados em nuvem
- **Dashboard**: Streamlit local (localhost:8501)
- **LLM (futuro)**: modelo local planejado, APIs pagas são opcionais

Nenhuma etapa do pipeline envia dados para fora da máquina.

## Consequências

**Positivas:**
- Zero custos recorrentes: sem assinaturas de API, cloud ou SaaS
- Privacidade total: dados financeiros nunca saem da máquina
- Funciona sem internet: avião, interior, queda de provedor
- Sem vendor lock-in: não depende de nenhum serviço específico
- Reprodutibilidade: mesmo ambiente sempre produz mesmo resultado

**Negativas:**
- OCR local (tesseract) tem qualidade inferior a serviços cloud (67% de acerto em kWh)
- Sem LLM local, categorização de transações ambíguas depende de regex manual
- Hardware local precisa ser razoável para LLM futuro (mínimo 16GB RAM para modelos pequenos)
- Sem backup automático em nuvem: responsabilidade do usuário manter backup
- Updates de dependências são manuais (sem CI/CD)

---

*"Quem troca liberdade por segurança não merece nenhuma das duas." -- Benjamin Franklin*
