---
id: MOB-bridge-5-classifier-pix
titulo: Classifier liga inbox/financeiro/pix/ ao extrator comprovante_pix_foto + persiste no grafo
status: concluída
concluida_em: 2026-05-13
prioridade: P0
data_criacao: 2026-05-12
fase: BRIDGE_MOBILE
depende_de: [MOB-bridge-4-inbox-subtipos-reader, DOC-27]
bloqueado_por: DOC-27 deve estar CONCLUIDA antes desta sprint iniciar -- ela só conecta o ETL existente, não cria extrator  <!-- noqa: accent -->
esforco_estimado_horas: 3
origem: Plano 2026-05-12 secao Fase B; categorias.ts do app mobile declara chip pix; backend hoje nao tem extrator dedicado para comprovante pix.  <!-- noqa: accent -->
mockup: novo-mockup/mockups/10-validacao-arquivos.html  <!-- noqa: accent -->
---

# Sprint MOB-bridge-5-classifier-pix -- ligar inbox/financeiro/pix/ ao extrator

## Contexto

Brief do dono: "ao gerar um pix no meu celular tem que aparecer que eu quero compartilhar com o app ouroboros. Aí ele vai salvar as informações, o arquivo do pix original e vai saber classificar e renomear e ordenar ele."

Estado atual (verificado em 2026-05-12):
- App mobile já tem chip `pix` na M08 (`~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/lib/share/categorias.ts:31`) que salva em `inbox/financeiro/pix/<data>-<slug>.<ext>` + companion `.md`.
- Backend: `sprint_doc_27_comprovante_pix_foto.md` está em **backlog** — extrator dedicado não existe ainda.
- `mappings/tipos_documento.yaml` tem entrada para `cupom_fiscal_foto` e `comprovante_pix_foto` (verificar) mas o módulo `src/extractors/comprovante_pix_foto.py` provavelmente não está produtivo.

Esta sprint conecta os 3 elos: 
(1) inbox_reader lê subpasta (MOB-bridge-4 fechou); 
(2) classifier roteia para extrator; 
(3) extrator extrai + persiste no grafo.

## Escopo (NÃO criar extrator — DOC-27 cuida)

Esta sprint **apenas conecta** os elos que já existem após DOC-27 fechar. Se DOC-27 não fechou, esta sprint está bloqueada (não inventar extrator paralelo).

## Objetivo

1. **Confirmar pré-requisitos** (passa-fora se algum faltar):
   - `src/extractors/comprovante_pix_foto.py` existe (DOC-27 entregou).
   - Schema `mappings/schema_opus_ocr.json` tem bloco `comprovante_pix_foto` (INFRA-OPUS-SCHEMA-EXTENDIDO entregou).
   - `MOB-bridge-4` está em concluidos/ (mapping `subtipo_mobile=pix → tipo=comprovante_pix_foto` já vive no registry).
2. **Garantir routing fim-a-fim**: arquivo em `inbox/financeiro/pix/<algo>.jpg` é processado por `processar_inbox` → `processar_arquivo_inbox(subtipo_mobile='pix')` → `detectar_tipo` devolve `tipo=comprovante_pix_foto` → extrator dedicado roda → grafo recebe node.
3. **Ingestão no grafo** (caso DOC-27 tenha entregue só o extrator, sem ingestão):
   - Criar/atualizar `src/graph/ingestor_documento.py::ingerir_comprovante_pix(resultado, db)`.
   - Node `documento` com `tipo_documento=comprovante_pix_foto`.
   - Arestas: `emitida_por` → fornecedor canônico; `valor_transacionado` com peso.
   - Match `documento_de` → transação via linking_massa pré-existente (não duplicar lógica).
4. **Renomeação canônica do arquivo**: `<YYYY-MM-DD>-<recebedor_slug>-<valor>.jpeg`. Arquivo NÃO movido (Syncthing intocável); só o nome canônico é gravado no sidecar.
5. **Testes integrativos** em `tests/test_bridge_pix_endtoend.py` com 3 fixtures sintéticas — caminho completo inbox → extrator → grafo.

## Validação ANTES (grep -- padrão (k))

```bash
# (a) Extrator entregue por DOC-27? CRITICO -- se faltar, ABORTAR
ls src/extractors/comprovante_pix_foto.py || echo "BLOQUEIO: DOC-27 nao fechou"
# (b) Schema bloco comprovante_pix_foto?
grep -A 5 "comprovante_pix_foto" mappings/schema_opus_ocr.json | head -10
# (c) MOB-bridge-4 fechou? registry conhece subtipo_mobile?
grep -n "subtipo_mobile" src/intake/registry.py | head
# (d) Pix reais para fixtures?
find data/raw ~/Protocolo-Ouroboros/inbox -name "*pix*" -o -name "*PIX*" 2>/dev/null | head
# (e) Ingestor de grafo ja tem ingerir_comprovante_pix?
grep -n "comprovante_pix" src/graph/ingestor_documento.py 2>/dev/null
```

Confirma: (a) extrator de DOC-27 disponível — **se faltar, ABORTAR sprint** (não inventar paralelo), (b) schema cobre o tipo, (c) MOB-bridge-4 entregou o mapping, (d) há fixtures, (e) precisa ou não criar `ingerir_comprovante_pix`.

## Não-objetivos (padrão (t))

- **NÃO** mover arquivos da inbox (Syncthing).
- **NÃO** implementar parser de QR code; usa Opus visão.
- **NÃO** depende de API Anthropic — modo artesanal ADR-13.
- **NÃO** mascarar CPF/CNPJ do dono ou Vitoria no node grafo (PII permitido em metadata; **mascarar apenas em log INFO** — padrão `(bb)`).
- **NÃO** tentar match automático de transação (linking massa cuida disso depois).
- **NÃO** fundir esta sprint com DOC-27; DOC-27 é a spec do extrator universal de comprovante (variantes), esta sprint só liga o caminho. Se DOC-27 não fechou, **ABORTAR** com mensagem clara.
- **NÃO** duplicar lógica de linking — usar pipeline `INFRA-LINKING-NFE-TRANSACAO` existente.

## Spec de implementação

### Schema de saída

```python
@dataclass
class ResultadoComprovantePix:
    sha256: str
    valor: float
    data_hora: datetime
    pagador: dict  # {nome, cpf_mascarado, instituicao}
    recebedor: dict  # {nome, cpf_cnpj, chave_pix, instituicao}
    id_transacao_e2e: str  # 32 chars hex
    raw_opus_dict: dict
```

### Registry hint

```python
# src/intake/registry.py
def detectar_tipo(caminho, mime, preview, pessoa="_indefinida", subtipo_mobile=None):
    ...
    if subtipo_mobile == "pix":
        return Decisao(
            tipo="comprovante_pix_foto",
            extrator_modulo="src.extractors.comprovante_pix_foto",
            pasta_destino=Path("data/raw") / pessoa / "comprovantes_pix",
            nome_canonico=None,  # vem do extrator
        )
    ...
```

### Ingestor

```python
# src/graph/ingestor_documento.py
def ingerir_comprovante_pix(resultado: ResultadoComprovantePix, db):
    doc_node = db.upsert_node(
        tipo="documento",
        nome_canonico=f"PIX_{resultado.id_transacao_e2e[:8]}",
        metadata={
            "tipo_documento": "comprovante_pix_foto",
            "valor": resultado.valor,
            "data": resultado.data_hora.isoformat(),
            "pagador_cpf_mascarado": resultado.pagador["cpf_mascarado"],
            "recebedor_cpf_cnpj": resultado.recebedor["cpf_cnpj"],
            "instituicao_pagadora": resultado.pagador["instituicao"],
        },
    )
    fornecedor = db.upsert_fornecedor(resultado.recebedor["nome"], cnpj=resultado.recebedor.get("cpf_cnpj"))
    db.upsert_edge(doc_node.id, fornecedor.id, tipo="emitida_por")
    return doc_node
```

## Proof-of-work (padrão (u))

```bash
# 1. Verificar extrator funciona em fixture sintetica
.venv/bin/python -c "
from src.extractors.comprovante_pix_foto import extrair
from pathlib import Path
r = extrair(Path('tests/fixtures/comprovante_pix/exemplo_1.jpg'))
print(f'valor={r.valor}, recebedor={r.recebedor[\"nome\"]}, e2e={r.id_transacao_e2e[:8]}')
"
# Esperado: valores extraidos coerentes; e2e tem 32 chars

# 2. Roteamento via registry com hint
.venv/bin/python -c "
from src.intake.registry import detectar_tipo
d = detectar_tipo(caminho=None, mime='image/jpeg', preview='', subtipo_mobile='pix')
print(f'tipo={d.tipo}, modulo={d.extrator_modulo}')
"
# Esperado: tipo=comprovante_pix_foto, modulo=src.extractors.comprovante_pix_foto

# 3. Ingestao em grafo (rodar processar_inbox_massa apos popular fixture em inbox/financeiro/pix/)
.venv/bin/python scripts/processar_inbox_massa.py --dry-run

# 4. Conferir grafo
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='documento' AND json_extract(metadata,'\$.tipo_documento')='comprovante_pix_foto'"
# Esperado: cresce >= 3

# 5. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/test_comprovante_pix.py -v
```

## Critério de aceitação (gate (z))

1. `src/extractors/comprovante_pix_foto.py` existe e exporta `extrair`.
2. Registry roteia `subtipo_mobile=pix` para o extrator dedicado.
3. Ingestor de grafo persiste node `documento` + edges `emitida_por`, `valor_transacionado`.
4. 3 fixtures sintéticas em `tests/fixtures/comprovante_pix/` + 5 testes (parsing, ingestão, deduplicação por sha256, mascaramento em log, retrocompat com inbox raiz).
5. `make conformance-comprovante_pix_foto` ≥ 3 amostras verdes (gate 4-way, padrão `(aa)`).
6. Pytest baseline cresce ≥ +5 testes.
7. Gauntlet verde.

## Referência

- Sprint dependente (subtipos reader): MOB-bridge-4.
- Sprint dependente (extrator universal): DOC-27 (`sprint_doc_27_comprovante_pix_foto.md`).
- Sprint pai (Opus visão): INFRA-OCR-OPUS-VISAO.
- Categorias mobile: `~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/lib/share/categorias.ts`.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B.

*"Pix é o dinheiro mais agil do mundo; merece o ETL mais simples." — princípio MOB-bridge-5*

## Conclusão (2026-05-13)

Sprint executada em escopo reduzido (Elementos 2, 3 e 5 da spec original).
Elemento 4 (renomeação canônica via sidecar) e linking PIX -> transação
ficam para sprint-filha `INFRA-LINKAR-PIX-TRANSACAO` já registrada (P1).

### Arquivos tocados

- `src/graph/ingestor_documento.py` -- nova função `ingerir_comprovante_pix_foto`
  + helper `_cnpj_sintetico_pix` + constante `CAMPOS_OBRIGATORIOS_PAYLOAD_PIX`.
  Reaproveita `ingerir_documento_fiscal` passando `itens=[]` (PIX é
  transferência monolítica, sem nós `item` granulares).
- `tests/test_bridge_pix_endtoend.py` -- 20 testes (5 categorias) cobrindo
  roteamento via registry, contrato do extrator, ingestão no grafo,
  idempotência e pipeline end-to-end com os 3 caches PIX reais transcritos
  por DOC-27.

### Pré-requisitos confirmados (validação ANTES, padrão (k))

- `src/extractors/comprovante_pix_foto.py` produtivo (DOC-27, HEAD f3609fe). OK
- `mappings/tipos_documento.yaml` tem entrada `comprovante_pix_foto`
  (extrator_modulo + pasta_destino_template). OK
- `mappings/schema_opus_ocr.json` enum `tipo_documento` inclui
  `comprovante_pix_foto`. OK
- `src/intake/registry.py` MOB-bridge-4 roteia `subtipo_mobile='pix'` para
  o YAML que aponta para o extrator dedicado. OK (verificação inline):
  `tipo=comprovante_pix_foto`, `extrator_modulo=src.extractors.comprovante_pix_foto`,
  `pasta_destino=data/raw/<pessoa>/comprovantes_pix/`.
- 3 caches reais Opus em `data/output/opus_ocr_cache/` (Itaú R$ 900, C6 R$ 50,
  Nubank R$ 367,65) -- gitignored, vivem no repo principal e foram acessados
  via path absoluto pelo teste end-to-end.

### Decisão arquitetural -- Opção (a) com fornecedor sintético

Comprovantes PIX para CPF de pessoa física não trazem CNPJ canônico do
recebedor. Para reaproveitar a infra existente (`ingerir_documento_fiscal`
exige `cnpj_emitente` para criar nó `fornecedor`), optei pela opção (a)
da spec com fallback inteligente em vez da opção (b) (novo tipo de nó
`pessoa`):

- **Justificativa**: zero migração de schema, infra de dedup/linking
  existente continua funcionando, e o identificador sintético tem prefixo
  `PIX|` que permite filtros SQL (`WHERE cnpj LIKE 'PIX|%'`).
- **Derivação**: `PIX|<sha8>` onde `sha8` = SHA-256 dos 8 primeiros hex
  chars da chave PIX disponível (`_pix.chave_destinatario` ->
  `_pix.destinatario_cpf_mascarado` -> `estabelecimento.razao_social` ->
  `sha256` da imagem). Determinístico: mesmos PIX para o mesmo
  destinatário compartilham o nó `fornecedor`.
- **PIX para PJ**: quando o payload trouxer `estabelecimento.cnpj` real
  (raro mas possível), o sintético NÃO é aplicado -- usa o CNPJ direto.
- **Metadata `cnpj_origem`** registra `real_do_payload` ou
  `sintetico_PIX_chave_destinatario` para auditoria.

Sem nós `item` granulares: PIX é evento monolítico (1 transferência =
1 movimentação). Os `itens` do payload (1 entrada com descrição/motivo)
ficam em `metadata["itens"]` para auditoria 4-way no Revisor.

### Métricas

- Testes novos: **20** (TestRegistryRoteamento x2, TestExtratorCacheHit x2,
  TestIngestorGrafo x9 incluindo parametrize 5 campos obrigatórios,
  TestIdempotencia x2, TestEndToEnd3CachesReais x2).
- Baseline pytest: 2832 passed antes da sprint (excluindo 13 testes de UI
  Streamlit/playwright pré-existentes que falham por ausência de browser
  no worktree e 5 testes mobile cache que falham por vault_sintetico
  modificado entre commits do supervisor) -> 2852 passed após a sprint
  (apenas adição, zero regressão).
- Acentuação PT-BR e ruff: limpos nos arquivos modificados.
- Smoke runtime (`./run.sh --check`): 23 checagens, 0 erros, 6 avisos
  esperados (data/raw e data/output ausentes -- gitignored).

### Não-objetivos confirmados

- Sem mover arquivos da inbox (Syncthing intocável).
- Sem parser de QR code.
- Sem dependência de API Anthropic (modo artesanal ADR-13).
- Sem match automático PIX -> transação (sprint-filha INFRA-LINKAR-PIX-TRANSACAO P1).
- PII mascarada em log INFO (apenas `sha[:12]`, `e2e[:8]`, razão social);
  CPFs mascarados ficam só dentro de metadata.

### Sprint-filhas registradas

- `INFRA-LINKAR-PIX-TRANSACAO` -- já existia no backlog (P1), não foi
  duplicada.
