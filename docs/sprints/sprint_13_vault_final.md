# Sprint 13 -- Integração Vault Final

## Status: Pendente
Issue: a criar

## Objetivo

Centralizar o ecossistema pessoal em um único sistema. Avaliar melhor estratégia de unificação entre os 3 projetos (Financas, Controle_de_Bordo_OS, vault Obsidian).

## Contexto dos 3 projetos

### Financas (este projeto)
- Pipeline ETL maduro, 38 arquivos Python, 2.859 transações
- Streamlit dashboard, 8 abas XLSX, gauntlet de testes

### Controle_de_Bordo_OS (~/Desenvolvimento/Controle_de_Bordo_OS)
- Blueprint arquitetural com hexagonal architecture (Ports & Adapters)
- Pydantic models, SQLite+WAL, event bus tipado, Luna bridge
- 20 sprints planejadas, escopo: finanças + hábitos + saúde + estudos + automação
- Typer CLI, Flet UI (desktop/mobile)

### Vault Obsidian (~/Controle de Bordo)
- 1.202 notas, 24 plugins (Dataview, Templater, QuickAdd, Tasks)
- Organização PARA: Pessoal, Trabalho, Projetos, Conceitos, Diário
- 44 relatórios financeiros + 7 metas via sync automático
- Scripts de automação em .sistema/ (inbox_processor, health_check, emoji_guardian)

## Entregas

- [ ] Avaliar estratégia: mover projeto pro vault vs vault pro projeto vs manter separados
- [ ] Se unificar: migrar storage de XLSX para SQLite+WAL (do Controle_de_Bordo_OS)
- [ ] Adotar Pydantic models para Transacao (substituir dicts)
- [ ] Implementar event bus tipado para desacoplamento do pipeline
- [ ] Integrar documentos pessoais (contratos, CVs, diplomas)
- [ ] Integrar documentos acadêmicos e profissionais
- [ ] Criar módulos novos (tracker acadêmico, carreira, saúde) -- se escopo aprovado
- [ ] Sync mobile (Obsidian Sync vs Syncthing vs Git)
- [ ] Unificar CLI (bash menu atual -> Typer CLI como no Controle_de_Bordo_OS)

## Conceitos a adotar do Controle_de_Bordo_OS

1. **Hexagonal Architecture**: domain/ nunca importa adapters/, DI via protocols
2. **Pydantic Models**: Transaction com validação tipada (substituir dicts informais)
3. **SQLite+WAL**: Storage ACID, backup trivial, queries SQL vs leitura de XLSX
4. **Event Bus**: Pub/Sub tipado para pipeline (extract_completed, transform_completed)
5. **Luna Bridge**: EventBusBridge para integração com Luna AI (futuro)
6. **4-Phase Migration**: JSON_ONLY -> DUAL_WRITE -> DUAL_READ_SQL -> SQLITE_ONLY

## Armadilhas conhecidas

- Mover o projeto pode quebrar paths relativos em scripts e imports
- Vault grande demora para sincronizar no mobile (1.5GB atualmente)
- Obsidian Sync é pago (alternativas: Syncthing, Git)
- Documentos sensíveis (contratos, diplomas) precisam de .gitignore especial
- SQLite migration precisa preservar 2.859 transações sem perda

## Critério de sucesso

Decisão arquitetural documentada em ADR. Se unificar: tudo centralizado, vault funcional no desktop e mobile, zero duplicação de dados.

## Dependências

Todas as sprints anteriores (especialmente Sprint 06 - Obsidian, Sprint 09 - Testes).
