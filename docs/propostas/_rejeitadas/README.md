# Propostas rejeitadas

Diretório-cemitério das propostas que o supervisor humano rejeitou. Cada arquivo `.md` aqui:

- Foi gerado pelo supervisor Opus principal (Claude Code interativo) em `docs/propostas/`.
- Recebeu `decisao_humana.status: rejeitada` com motivo no frontmatter.
- Foi movido para cá para auditabilidade.

## Por que manter histórico

A Sprint LLM-06-V2 (SHA-guard) impede que a mesma proposta seja regenerada em sessão futura: antes de criar uma proposta nova, o supervisor calcula sha256 da hipótese normalizada e checa se já existe um match em `_rejeitadas/`. Match → aborta + mostra motivo da rejeição original.

Sem este histórico, sessões diferentes podem regenerar propostas idênticas e o humano revisa o mesmo lixo várias vezes.

## Convenção de nome

`<id-original>__<YYYY-MM-DD>.md` — preserva o id da proposta original e adiciona a data de rejeição.

## Não delete arquivos daqui

Mesmo se a proposta parecer obsoleta, mantenha o histórico. O custo de armazenamento é nulo e o valor de auditabilidade cresce com o tempo.
