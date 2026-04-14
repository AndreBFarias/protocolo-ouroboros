# ADR-06: Integração com vault Obsidian

## Status: Aceita

## Contexto

O usuário já possui vault Obsidian em `~/Controle de Bordo/` com estrutura PARA (Projects, Areas, Resources, Archives). Os relatórios financeiros mensais precisam estar acessíveis dentro do workflow de notas existente, com possibilidade de queries Dataview para agregações automáticas.

Alternativas consideradas:
- **Symlinks**: simples, mas Obsidian nem sempre segue symlinks corretamente em todos os OS.
- **Cópia manual**: não escala, usuário esquece.
- **Plugin Obsidian customizado**: overkill, exige manutenção em TypeScript.

## Decisão

Criar módulo `src/obsidian/sync.py` que sincroniza automaticamente:
- 44 relatórios mensais para `~/Controle de Bordo/Pessoal/Financeiro/Relatórios/`
- 7 notas de metas
- MOC (Map of Content) com dashboard financeiro usando Dataview queries
- Cada arquivo inclui frontmatter YAML com metadados (mes_ref, receita, despesa, saldo) para queries Dataview

## Consequências

**Positivas:**
- Relatórios acessíveis diretamente no Obsidian, integrados ao fluxo de notas
- Frontmatter YAML permite queries Dataview (ex: tabela de saldos mensais, alertas)
- MOC centraliza acesso a todos os relatórios financeiros
- Sync é idempotente: rodar múltiplas vezes não duplica conteúdo

**Negativas:**
- Duplicação de dados: relatórios existem em `data/output/` e no vault Obsidian
- Dataview queries não validadas completamente (pendente Sprint 6)
- Dependência implícita: se estrutura do vault mudar, sync quebra silenciosamente
- Caminho do vault é hardcoded (`~/Controle de Bordo/`), precisa ser configurável

---

*"A ordem é a primeira lei do céu." -- Alexander Pope*
