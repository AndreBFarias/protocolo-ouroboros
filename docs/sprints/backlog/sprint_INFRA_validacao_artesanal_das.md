---
id: "INFRA-VALIDACAO-ARTESANAL-DAS  <!-- noqa: accent -->"
titulo: "Validacao artesanal DAS PARCSN -- 2 amostras lidas por Opus multimodal versus ETL (alto dano fiscal)  <!-- noqa: accent -->"
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: [INFRA-OPUS-SCHEMA-EXTENDIDO]
esforco_estimado_horas: 2
origem: "Plano 2026-05-12 secao Fase A1 -- DAS PARCSN tem 19 nodes; dano fiscal alto (DARF da Receita); ground-truth cristalino; AUDIT2-SPRINT107-RETROATIVA pendente (14 nodes pre-Sprint 107 sem fornecedor sintetico).  <!-- noqa: accent -->"
mockup: "novo-mockup/mockups/10-validacao-arquivos.html  <!-- noqa: accent -->"
---

# Sprint INFRA-VALIDACAO-ARTESANAL-DAS -- prova de paridade ETL × Opus em DAS PARCSN  <!-- noqa: accent -->

## Contexto

19 nodes DAS PARCSN no grafo (`data/output/grafo.sqlite`). Sprint 107 introduziu fornecedor sintético RECEITA_FEDERAL para entidades fiscais; AUDIT2-SPRINT107-RETROATIVA (~1h, backlog) cuida de backfill nos 14 nodes pré-Sprint 107.

DAS PARCSN é o parcelamento ativo do Simples Nacional do CNPJ MEI desativado do André (45.850.636/0001-60, 25 parcelas, atualmente 17ª). Cada DAS errado é multa/juros adicional pela Receita. Validar com Opus = defesa em camadas para o dinheiro do casal.

Ground-truth é cristalino: PDF gerado pelo PortalDAS-Receita Federal traz `principal`, `multa`, `juros`, `total a recolher`, `data limite pagamento`, `código de barras 47 dígitos`, `competência`.

## Objetivo

1. Selecionar 2 DAS PARCSN reais: idealmente 1 pré-Sprint 107 (sem fornecedor sintético) + 1 pós-Sprint 107.
2. Para cada um:
   - Capturar dict ETL via extrator atual (verificar nome via `grep -r "das_parcsn" src/extractors/`).
   - Capturar dict Opus via Read multimodal sobre PDF.
   - Persistir cache no schema canônico estendido (com `codigo_barras`, `vencimento`, `competencia`).
   - Confrontar com lançamento correspondente no extrato bancário (`mes_ref` do pagamento).
   - Diff campo-a-campo.
3. Confirmar empíricamente: o fornecedor canônico está `RECEITA_FEDERAL` ou ainda `DAS PARCSN ANDRE` (drift pré-107)? Tag IRPF `imposto_pago` corretamente atribuída?
4. Relatório `docs/auditorias/VALIDACAO_ARTESANAL_DAS_2026-MM-DD.md`.

## Validação ANTES (grep -- padrão (k))

```bash
ls data/raw/andre/impostos/das_parcsn/   # esperado: >= 2 PDFs reais
sqlite3 data/output/grafo.sqlite "SELECT json_extract(metadata,'\$.competencia'), json_extract(metadata,'\$.razao_social_fornecedor'), json_extract(metadata,'\$.contribuinte') FROM node WHERE tipo='documento' AND json_extract(metadata,'\$.tipo_documento') IN ('das_parcsn','das_parcsn_andre') ORDER BY 1"
.venv/bin/python -c "from src.extractors.das_parcsn_pdf import ExtratorDASPARCSNPDF; print('importa OK')"
grep -n "RECEITA_FEDERAL" mappings/fornecedores*.yaml
```

Confirma: (a) há ≥ 2 PDFs DAS reais, (b) grafo tem 19 nodes com fornecedor — algum ainda mostra "DAS PARCSN" em vez de "RECEITA_FEDERAL"?, (c) extrator existe, (d) fornecedor sintético declarado em mapping.

## Não-objetivos (padrão (t))

- **NÃO** corrigir os 14 nodes pré-Sprint 107 nesta sprint — AUDIT2-SPRINT107-RETROATIVA cuida.
- **NÃO** baixar novos DAS do PortalDAS (escopo é validação local).
- **NÃO** mascarar o CNPJ do MEI desativado em log INFO — é CNPJ corporativo público, não PII pessoal.
- **NÃO** alterar o parcelamento (zero ação fiscal real desta sprint; só leitura).
- **NÃO** modificar `mappings/fornecedores_sinteticos.yaml` sem ADR-update.

## Spec de implementação

### Diferença 1 — Schema estendido (das_parcsn)

```python
dict_opus_das = {
    "sha256": "...",
    "tipo_documento": "das_parcsn",
    "estabelecimento": {"razao_social": "RECEITA FEDERAL DO BRASIL", "cnpj": "00.394.460/0058-87"},
    "contribuinte": {"cpf_cnpj_mascarado": "XX.XXX.XXX/0001-60", "razao_social": "ANDRE DA SILVA BATISTA DE FARIAS - MEI"},
    "data_emissao": "YYYY-MM-DD",
    "competencia": "YYYY-MM",
    "vencimento": "YYYY-MM-DD",
    "numero_da_inscricao": "...",
    "principal": ...,
    "multa": ...,
    "juros": ...,
    "total": ...,
    "codigo_barras": "<47 digitos>",
    "forma_pagamento": "boleto_bancario",
    "extraido_via": "opus_v4_7_artesanal",
    "confianca_global": ...,
    "ts_extraido": "..."
}
```

### Diferença 2 — Cross-check extrato bancário

Cada DAS pago tem lançamento espelho no extrato (`data/output/ouroboros_2026.xlsx`, aba extrato). Categoria esperada: `Imposto`. Quem: `Andre`. Tag IRPF: `imposto_pago`.

```python
import pandas as pd
df = pd.read_excel("data/output/ouroboros_2026.xlsx", sheet_name="extrato")
match = df[
    (df["data"] == dict_opus_das["vencimento"]) &
    (df["valor"].between(dict_opus_das["total"] - 0.01, dict_opus_das["total"] + 0.01)) &
    (df["tipo"] == "Imposto")
]
assert len(match) >= 1, "DAS sem batimento no extrato!"
assert match.iloc[0]["tag_irpf"] == "imposto_pago", "Tag IRPF errada"
```

### Diferença 3 — Aritmética principal + multa + juros = total

Defesa em camadas (padrão `(n)`): garantir `abs(principal + multa + juros - total) < 0.01`. Falha → erro classe A no relatório.

### Diferença 4 — Fornecedor canônico verificado

```bash
# Verificar se node do grafo aponta para RECEITA_FEDERAL
sqlite3 data/output/grafo.sqlite "
  SELECT n.nome_canonico, n.metadata
  FROM node n
  JOIN edge e ON e.dst = n.id
  WHERE e.src = (SELECT id FROM node WHERE sha256_arquivo = '<sha do das>')
    AND e.tipo = 'emitida_por'
"
# Esperado pos-Sprint 107: nome_canonico = "RECEITA FEDERAL DO BRASIL"
# Pre-Sprint 107: pode aparecer "DAS PARCSN ANDRE" -- flag em relatorio
```

## Proof-of-work (padrão (u))

```bash
# 1. Listar DAS PARCSN reais
find data/raw -name "*DAS*" -o -name "*das_parcsn*" -type f | head -5

# 2. Rodar extrator (API canonica: ExtratorDASPARCSNPDF.extrair_das devolve dict)
.venv/bin/python -c "
from src.extractors.das_parcsn_pdf import ExtratorDASPARCSNPDF
from pathlib import Path
caminho = Path('data/raw/andre/impostos/das_parcsn/<arquivo>.pdf')
resultado = ExtratorDASPARCSNPDF(caminho).extrair_das(caminho)
doc = resultado['documento']
print(f'comp={doc.get(\"periodo_apuracao\")}, total={doc.get(\"total\")}, cnpj={doc.get(\"cnpj_emitente\")}, parcela={doc.get(\"parcela_atual\")}/{doc.get(\"parcela_total\")}')
"

# 3. Confirmar aritmetica
.venv/bin/python -c "
# r.principal + r.multa + r.juros must equal r.total
"

# 4. Cross-check extrato
.venv/bin/python -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
das_lancamentos = df[df['categoria']=='Imposto'][['data','valor','mes_ref','tag_irpf']].sort_values('data')
print(das_lancamentos.tail(20))
"

# 5. Cache populado
ls data/output/opus_ocr_cache/ | wc -l
# Esperado: cresce >= 2 entradas tipo das_parcsn

# 6. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/ -k "das_parcsn or imposto" -q
```

## Critério de aceitação (gate (z))

1. 2 DAS PARCSN processados (1 pré-Sprint 107 + 1 pós-Sprint 107 quando possível).
2. Cache cresce ≥ 2 entradas com `tipo_documento=das_parcsn`.
3. Aritmética `principal + multa + juros = total` verificada e documentada para cada amostra.
4. Cross-check extrato bancário rodado: cada DAS bate (R$ 0,00 diferença) com lançamento `tipo=Imposto`, `tag_irpf=imposto_pago`, `quem=Andre`.
5. Fornecedor canônico verificado no grafo (`RECEITA FEDERAL` ou flag de drift pré-107).
6. Relatório `docs/auditorias/VALIDACAO_ARTESANAL_DAS_<data>.md` existe.
7. Veredito declarado.
8. Se REPROVADO ou ressalva: sprint-filha (`sprint_das_fix_*.md` ou ativa AUDIT2-SPRINT107-RETROATIVA).
9. Gauntlet verde.

## Referência

- Sprint 107 (fornecedor sintético): commit `b470024` (2026-04-28).
- AUDIT2-SPRINT107-RETROATIVA: backlog em `docs/sprints/backlog/sprint_AUDIT2_*.md` (parcial — verificar nome canônico).
- Extrator canônico: `src/extractors/das_parcsn_pdf.py::ExtratorDASPARCSNPDF` (ExtratorBase). Método-chave `extrair_das(caminho, texto_override=None)` retorna `dict` com chaves `documento`, `texto`, `_erro_extracao`. Documento expõe: `total`, `cnpj_emitente`, `periodo_apuracao`, `parcela_atual`, `parcela_total`, `data_emissao`, `data_vencimento`.
- Sprint-pai schema: INFRA-OPUS-SCHEMA-EXTENDIDO.
- Mapeamento fornecedor: `mappings/fornecedores_sinteticos.yaml`.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase A1.

*"Imposto errado é multa que volta no proximo mes; validar o DAS é poupar a Receita do trabalho de cobrar." — princípio INFRA-VALIDACAO-ARTESANAL-DAS*  <!-- noqa: accent -->
