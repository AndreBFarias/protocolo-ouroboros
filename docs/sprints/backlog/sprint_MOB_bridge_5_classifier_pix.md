---
id: MOB-bridge-5-classifier-pix
titulo: Classifier liga inbox/financeiro/pix/ ao extrator comprovante_pix_foto + persiste no grafo
status: backlog
concluida_em: null
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
