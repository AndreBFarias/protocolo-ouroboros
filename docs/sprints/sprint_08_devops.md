# Sprint 08 - Testes, CI e Robustez

## Objetivo

Estabelecer infraestrutura de testes automatizados, integração contínua e mecanismos de proteção de dados. Garantir que o pipeline seja confiável, mensurável e seguro.

## Entregas

- [ ] Testes automatizados com fixtures fictícias (dados financeiros sintéticos)
- [ ] Coverage >= 80% em módulos críticos (extratores, categorizador, deduplicador)
- [ ] GitHub Actions CI: pytest + ruff em cada push/PR
- [ ] Schema versioning: versionamento explícito do formato de dados interno
- [ ] Migrador automático de schema (atualiza dados antigos para formato corrente)
- [ ] Backup automático antes de processar (snapshot do estado anterior)
- [ ] Logging estruturado: arquivo processado, páginas extraídas, transações encontradas, tempo de execução
- [ ] Health check do pipeline: ./run.sh --check (verifica dependências, paths, integridade)

## Dependências

Sprint 4+ (categorização inteligente e validação já implementados).

## Critério de Sucesso

CI verde no GitHub Actions. Coverage >= 80%. `./run.sh --check` passa sem erros em ambiente limpo.

## Estimativa de Complexidade

**Média.** Itens individualmente simples, mas volume de cobertura de testes e configuração de CI exigem disciplina. Estimativa: 2 semanas.
