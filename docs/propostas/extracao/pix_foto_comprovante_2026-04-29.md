---
id: pix_foto_comprovante
tipo: extracao
data_proposta: 2026-04-29
proponente: opus-supervisor
hipotese: |
    Tipo de documento `pix_foto_comprovante` aparece em data/raw/ ou inbox/ mas o classifier retorna None. Propor extrator dedicado em `src/extractors/pix_foto_comprovante.py` + regra em `mappings/tipos_documento.yaml`. Amostra de referência: `data/raw/_classificar/comprovante_pix.jpg`.
evidencia:

    - amostra: data/raw/_classificar/comprovante_pix.jpg
    - sub-spec sugerida: docs/sprints/backlog/sprint_doc_<X>_extrator_pix_foto_comprovante.md
sha: deca32fd9a699aec
decisao_humana:
    status: pendente   # pendente | aprovada | rejeitada
    data: null
    motivo: null
    aplicada_em: null  # commit SHA quando merge para mappings/ ou backlog/
---

# Proposta: extrator para `pix_foto_comprovante`

## Contexto

O tipo `pix_foto_comprovante` foi detectado em runtime (classifier retornou None) e não tem extrator dedicado. Proposta gerada via `scripts/propor_extrator.py` para iniciar o ciclo de revisao humana.

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
