---
id: <slug-curto-kebab-case>
tipo: <regra_categoria | extracao | resolver | classificacao | er_produtos | linking | outro>
data_proposta: 2026-04-28
proponente: opus-supervisor
hipotese: |
    Texto livre em uma frase: o que esta proposta resolveria.
evidencia:
    - <amostra ou query do grafo que motivou a proposta>
    - <link para arquivo em data/raw/ ou node id no grafo>
sha: <sha256 da hipotese normalizada -- preencher antes de gerar; ver scripts/check_propostas_rejeitadas.py>
decisao_humana:
    status: pendente   # pendente | aprovada | rejeitada
    data: null
    motivo: null
    aplicada_em: null  # commit SHA quando merge para mappings/ ou backlog/
---

# Proposta: <título humano>

## Contexto

Por que esta proposta surgiu? Qual a observação que motivou?

## Mudança proposta

Diff conceitual ou bloco de YAML/Python:

```yaml
# antes
categoria: Outros

# depois
categoria: Padaria
regra: razao_social ~ "(?i)Ki-Sabor" AND valor < 800
```

## Trade-offs considerados

- Alternativa A: ...
- Alternativa B: ...
- Por que esta foi escolhida.

## Como aprovar

1. Humano revisa via tab "Proposições" no Revisor (ver Sprint LLM-05-V2) **ou** lê este `.md` direto.
2. Marca `decisao_humana.status: aprovada` + `data` + `aplicada_em` (commit SHA).
3. Roda script de aplicação (ex: `scripts/aplicar_proposta_regra.py`) ou faz Edit manual.
4. Move esta proposta para `docs/propostas/_aprovadas/` para auditabilidade.

## Como rejeitar

1. Marca `decisao_humana.status: rejeitada` + `motivo` claro.
2. Move esta proposta para `docs/propostas/_rejeitadas/`.
3. Sprint LLM-06-V2 (SHA-guard) impede regenerar a mesma proposta no futuro.
