---
id: INFRA-LINKAR-PIX-TRANSACAO  # noqa: accent
titulo: Linker comprovante PIX foto -> transação no extrato bancário  # noqa: accent
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-13
fase: ETL
depende_de:
  - DOC-27  # comprovante_pix_foto (concluída em 2026-05-13)
esforco_estimado_horas: 4
origem: sprint DOC-27 entregou classifier + extrator + 3 caches reais, mas não ingere PIX no grafo nem amarra com transação no extrato. Falta o linker.
---

# Sprint INFRA-LINKAR-PIX-TRANSACAO  <!-- noqa: accent -->

## Contexto

Sprint DOC-27 (concluída em 2026-05-13) entregou:

- Entrada YAML `comprovante_pix_foto` em `mappings/tipos_documento.yaml`
- Extrator `src/extractors/comprovante_pix_foto.py` que delega ao Opus visão
- 3 caches canônicos transcritos artesanalmente (Itaú/C6/Nubank)
- 17 testes verdes

Mas o extrator devolve `[]` de Transacao — a transação real chega pelo extrato bancário. O PIX foto é metadado complementar que precisa ser amarrado.

## Hipótese

`src/graph/linking.py` já tem a heurística `data_valor_aproximado` que amarra documento->transação. Para PIX, podemos:

1. Criar `ingerir_comprovante_pix_foto(db, payload_opus, caminho)` análogo a `ingerir_cupom_foto`, mas:
   - Chave canônica do documento: `PIXFOTO|<sha256>`
   - Não cria nó `fornecedor` (PIX vai para CPF de pessoa física, não tem CNPJ canônico)
   - OU cria nó `pessoa` (analogia ao `fornecedor`) com identificador `PIX|<chave_pix>`
2. Pipeline `./run.sh --inbox` chama o extrator → `ingerir_comprovante_pix_foto` → grafo
3. `linking_documento_transacao` rotineiro casa PIX (`data_emissao` + `total`) contra transação no extrato com `descricao` contendo "PIX" ou "TRANSF".

## Decisão arquitetural pendente

Schema do grafo: PIX para CPF cria nó `pessoa` ou estende `fornecedor` para aceitar CPF mascarado? Recomendação: criar nó `pessoa` (`PIX|<chave_pix>`) como tipo separado. Documentar em ADR-30 rascunho.

## Proof-of-work esperado

```bash
# Antes do fix: 3 caches PIX existem mas nenhum nó documento no grafo
.venv/bin/python -c "
from src.graph.db import GrafoDB, caminho_padrao
db = GrafoDB(caminho_padrao())
cur = db.con.execute(\"SELECT COUNT(*) FROM no WHERE tipo='documento' AND chave LIKE 'PIXFOTO|%'\")
print(f'PIX documentos: {cur.fetchone()[0]}')  # 0 antes
"

# Após fix:
./run.sh --inbox  # processa 3 fotos
# Esperado: 3 nós documento PIXFOTO|*, 3 arestas para transações no extrato
```

## Padrões canônicos aplicáveis

- (s) Validação ANTES: confirmar que as 3 transações PIX EXISTEM no extrato bancário (data + valor batem).
- (q) Cobertura granular: aresta `documento_de` para cada PIX.
- (e) PII em 4 sítios: identidade da pessoa destinatária pode aparecer em 4 sítios distintos (grafo, drill-down, xlsx, dashboard).

## Acceptance criteria

- 3 caches PIX existentes geram 3 nós `documento` no grafo.
- 3 arestas `documento_de` ligam cada PIX à transação correspondente.
- `make smoke` 10/10.
- Pytest baseline >= 2879.
- ADR-30 rascunho com decisão pessoa vs fornecedor.

---

*"Comprovante é eco; transação é onda. Linkar é responsabilidade." -- princípio do arquivista PIX*
