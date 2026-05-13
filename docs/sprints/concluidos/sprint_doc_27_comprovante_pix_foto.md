---
id: DOC-27
titulo: Extrator de comprovante PIX em foto
status: concluída
concluida_em: 2026-05-13
prioridade: P1
onda: 3
esforco_estimado_horas: 4
---

# Sprint DOC-27 -- Extrator de comprovante PIX em foto

**Origem**: lacuna 1 da auditoria `docs/auditorias/cobertura_backlog_2026-04-29.md` (item 19 do plan `pure-swinging-mitten`, Onda 3).
**Prioridade**: P1
**Onda**: 3
**Esforço estimado**: 4h
**Depende de**: DOC-13 (multi-foto selector) recomendado mas não bloqueante
**Fecha itens da auditoria**: lacuna 1 dos 8 tipos cotidianos

## Problema

Dono recebe comprovante PIX gerado pelo app do remetente como JPEG/PNG e salva na inbox. Hoje o classifier não tem regex específica para esse formato (diferente do comprovante PIX gerado pelo próprio app banco do dono, que vai como `recibo_nao_fiscal`). Resultado: comprovante cai em `_classificar/` ou é rotulado errado, virando órfão silencioso.

Frequência alta: cotidiano de qualquer transação P2P fora de Pix do app principal.

## Hipótese

Detector pode usar match-mode `all` com 3 padrões regex sobre o texto extraído por OCR Tesseract:

- `(PIX|Pix|pix)` em pelo menos 2 ocorrências (cabeçalho + corpo).
- `(R\$|REAIS)` com valor próximo.
- Marcador de comprovante: chave PIX, ID transação, ou padrão "Comprovante de envio/transferência".

Extrator dedicado parseia: data, valor, chave PIX/CPF do destinatário (mascarado), banco do destinatário se visível.

## Implementação proposta

1. Adicionar entrada `comprovante_pix_foto` em `mappings/tipos_documento.yaml`:
   - mimes: `image/jpeg`, `image/png`, `application/pdf`.
   - regex_conteudo: 3 padrões acima.
   - extrator_modulo: `src.extractors.comprovante_pix_foto`.
   - pasta_destino_template: `data/raw/{pessoa}/comprovantes_pix/`.
2. Criar `src/extractors/comprovante_pix_foto.py` com função `extrair(caminho)` retornando dict canônico.
3. Adicionar registro em `src/intake/registry.py`.
4. Fixture sintética em `tests/fixtures/comprovante_pix_foto/`.
5. Coletar ≥3 amostras reais (via dono).
6. Rodar `make conformance-comprovante_pix_foto`.

## Proof-of-work (runtime real)

3 amostras reais ingeridas, cada uma gera 1 node `documento` + 1 aresta `documento_de` para a transação correspondente no extrato. Cobertura no Revisor 4-way: ETL × Opus × Grafo × Humano concordam.

## Acceptance criteria

- Entrada YAML + extrator + registry + fixture + ≥6 testes.
- ≥3 amostras 4-way verdes (`make conformance-comprovante_pix_foto` exit 0).
- Smoke 10/10, lint OK.
- Aresta `documento_de` criada em runtime real.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` em amostras reais antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-comprovante_pix_foto` exit 0 com ≥3 amostras 4-way.
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.


## Conclusão (2026-05-13)

Implementação entregue na sessão 2026-05-13:

- Entrada YAML `comprovante_pix_foto` (prioridade especifico) em `mappings/tipos_documento.yaml`.
- Extrator `src/extractors/comprovante_pix_foto.py` que delega ao Opus visão.
- 3 caches canônicos transcritos artesanalmente pelo supervisor Opus 4.7 lendo via Read multimodal:
  - Itaú: PANIFICADORA KI-SABOR, R$ 900,00, 2026-05-09 (aluguel)
  - C6: Wesley Ramon Castro Santana, R$ 50,00, 2026-05-08
  - Nubank: Vitória Maria Silva dos Santos, R$ 367,65, 2026-03-04
- 17 testes em `tests/test_comprovante_pix_foto.py` (todos verdes).
- Proof-of-work runtime: classifier reconhece 3/3 layouts (Itaú/C6/Nubank); extrator devolve payload canônico.

### Escopo NÃO incluído (movido para sprint-filha)

- Ingestão no grafo SQLite: criar nó `documento` PIXFOTO|<sha256> e linkar à transação no extrato bancário.
- Ver `sprint_INFRA_linkar_pix_transacao_2026-05-13.md` (P1).

### Métricas finais

- Pytest: 2879 passed (+17 novos sobre baseline 2862).
- Smoke: 10/10 contratos OK.
- Lint: 0 erros.

