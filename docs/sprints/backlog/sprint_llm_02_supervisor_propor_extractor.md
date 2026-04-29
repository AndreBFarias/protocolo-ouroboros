# Sprint LLM-02 -- Supervisor propõe spec de extractor quando classifier=None

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 2
**Esforço estimado**: 6h
**Depende de**: LLM-01
**Fecha itens da auditoria**: item 19 da auditoria (8 documentos sem regra YAML)

## Problema

Quando classifier não reconhece tipo, arquivo cai em _classificar/ sem disparar nenhuma ação. Resultado: documento órfão silencioso.

## Hipótese

Integrar Supervisor no fluxo: ao detectar tipo desconhecido, chamar LLM com amostra OCR + pedido de spec. Output YAML em mappings/proposicoes/. Marca arquivo como 'aguardando_extractor' no relatório anti-órfão.

## Implementação proposta

1. supervisor.propor_extractor(amostra: str) -> SugestaoExtractor.
2. Schema Pydantic com tipo, regex_tentativa, campos_a_extrair.
3. Output em mappings/proposicoes/YYYY-MM-DD_HHMM_<topico>.yaml.
4. Hook em src/intake/registry.py quando classifier retorna None.
5. SHA-guard: proposta com mesmo SHA não duplica.

## Proof-of-work (runtime real)

Subir PDF Amazon (tipo desconhecido) em _classificar/ → após inbox rodar, mappings/proposicoes/ tem 1 YAML novo com sugestão.

## Acceptance criteria

- Diretório mappings/proposicoes/ + .gitkeep.
- Schema Pydantic versionado.
- Hook em registry.py disparado em runtime real.
- 8+ testes (cache, idempotência, schema válido, fallback offline).

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` exit 0 quando aplicável (>=3 amostras 4-way).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
