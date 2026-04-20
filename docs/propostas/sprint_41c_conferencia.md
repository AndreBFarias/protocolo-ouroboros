---
id: 2026-04-19_sprint_41c_conferencia
tipo: conferencia_artesanal
sprint: 41c
data: 2026-04-19
status: aprovada
autor_proposta: supervisor-artesanal-claude-code
---

# Conferência Artesanal Opus -- Sprint 41c (Unificação detector legado + YAML)

## Setup

- Script: `python scripts/sprint41_prova_fogo.py --pasta data/raw`
- 98 arquivos varridos recursivamente em `data/raw/{andre,vitoria}/`
- Suíte: 191/191 testes passando (177 antigos + 14 novos do registry)
- Lint limpo

## Resultado

```
PRÉ-41c (recall 19%):                  PÓS-41c (recall 85%):
- _NAO_CLASSIFICADO_:    79             - _NAO_CLASSIFICADO_:    15
- holerite:              15             - bancario_nubank_cc:    16
- boleto_servico:         4             - bancario_nubank_cartao:12
                                         - bancario_santander_cartao:14
                                         - holerite:              15
                                         - bancario_itau_cc:       4
                                         - bancario_c6_cartao:     3
                                         - boleto_servico:         4
                                         - bancario_nubank_ofx:    2
                                         - bancario_c6_cc:         1
                                         - bancario_c6_ofx:        1
                                         - (etc)

Total artefatos:  98     Total artefatos:  98
Roteados:         19     Roteados:         83  (+64)
Em _classificar/: 79     Em _classificar/: 15  (-64)
RECALL:          19%     RECALL:          85%
```

## Os 15 residuais em `_classificar/` -- todos identificados

Todos são `document(N).pdf` (N de 2 a 11, alguns com sufixo "(1)") -- **holerites Infobase escaneados sem texto extraível**. Confirmação:

```bash
for f in /tmp/sprint41_prova_*/data/raw/_classificar/_CLASSIFICAR_*.pdf; do
  pdfinfo "$f" 2>/dev/null | grep -E "^Pages|^Producer"
done
# todos: 1 página, scan
```

São cobertos pela **Sprint 45 (OCR de PDF)**. Quando a 45 entrar e roduar OCR antes da classificação, esses 15 viram `holerite` (recall sobe para 100%).

## Checklist de conferência

| # | Pergunta | Resultado |
|---|----------|-----------|
| 1 | Sem duplicação? CSV/XLS/XLSX usam só `file_detector` legado? | OK -- registry delega 100% para legado em mimes bancários |
| 2 | PDFs documentais (cupom_garantia, holerite, NFC-e) ainda funcionam pelo YAML? | OK -- legado retorna None para não-Itaú/Santander, YAML pega |
| 3 | OFX coberto (legado não cobre)? | OK -- detector simples no registry, banco extraído do nome, pessoa via path |
| 4 | Adapter `DeteccaoArquivo -> Decisao` preserva pessoa, banco, período? | OK -- pasta `<pessoa>/<banco>_<tipo>/`, nome `BANCARIO_<BANCO>_<TIPO>_<periodo>_<sha8>.<ext>` |
| 5 | Origem da decisão rastreável? | OK -- `Decisao.origem_sprint == "41c"` para legado, `41` para YAML |
| 6 | Precisão mantida? | OK -- 83/83 inspecionados, todos no banco/tipo correto. Zero falsos-positivos |
| 7 | XLS sem senha levanta exceção? | OK -- registry captura via `_detectar_legado_silencioso`, delega para YAML (que devolve fallback `_classificar/`) |
| 8 | Integração com orchestrator não quebra testes existentes? | OK -- 191/191 passando, incluindo testes pré-41c |

## Critério de aceitação

A sprint declarava **recall >= 95%** como meta. **Atingiu 85% pós-41c.**

A divergência é explicada e aceita: os 15 holerites Infobase escaneados (15.3% do total) são SCAN sem texto extraível. Sem OCR de PDF (Sprint 45), nenhum detector consegue extrair pista; cair em `_classificar/` é o comportamento correto até a Sprint 45 entrar.

**Recall efetivo do escopo da 41c (CSV + XLS + XLSX + OFX + PDF nativo bancário): 100%.** Nenhum arquivo dentro do escopo da sprint ficou em `_classificar/`. Os residuais são fora do escopo (depende de OCR).

Decisão: aceitar 85% como sucesso da 41c, com nota explícita de que 100% chega após Sprint 45.

## Decisão arquitetural confirmada -- legado e YAML coexistem

A 41c provou que **não há necessidade de migrar `file_detector.py` para YAML.** As duas abordagens cobrem domínios distintos:

- **YAML declarativo:** assinaturas textuais (regex) -- bom para tipos documentais (NF, garantia, holerite, cupom). Adicionar novo tipo é editar arquivo.
- **Detector procedural:** lê headers de CSV, decripta XLS com msoffcrypto, parseia OFX -- bom para formatos bancários. Tentar declarar isso em YAML viraria gambiarra (ex.: como descrever "decripta XLS, lê coluna 1, extrai período da data" em regex?).

O registry é a porta única que orquestra os dois sem conhecer detalhes. Manutenção continua descentralizada (YAML para tipos novos documentais; `file_detector.py` para novos bancos).

## Decisão humana

**Aprovada em:** 2026-04-19

**Notas do humano:**

Sprint 41c fechada. Recall 85% é o teto até a Sprint 45 entrar com OCR. Precisão 100% mantida.

Os 15 residuais (`document(N).pdf` Infobase escaneados) NÃO bloqueiam a integração no `inbox_processor.py`: são holerites já presentes em `data/raw/andre/holerites/` por caminhos antigos -- intake universal só os encontraria se chegassem novos pela inbox/, e nesse caso o supervisor (humano) reconhece e processa via OCR manual ou aguarda Sprint 45.

Próximo: Sprint 41b (auto-detect pessoa) ou direto integrar no `inbox_processor.py` -- decisão fora do escopo desta conferência.

---

*"Dois caminhos para o mesmo destino é um caminho perdido." -- princípio da unificação arquitetural*
