---
id: INFRA-VALIDACAO-ARTESANAL-HOLERITE
titulo: Validacao artesanal holerite -- 2 amostras (1 G4F + 1 Infobase) lidas por Opus multimodal versus ETL
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: [INFRA-OPUS-SCHEMA-EXTENDIDO]
esforco_estimado_horas: 2
origem: Plano 2026-05-12 secao Fase A1 -- holerite 24/24 declarado verde mas auditoria nunca cruzou ETL × Opus campo-a-campo. Suspeito mascarar erro silencioso (G4F vs Infobase tem layouts divergentes).  <!-- noqa: accent -->
mockup: novo-mockup/mockups/10-validacao-arquivos.html  <!-- noqa: accent -->
---

# Sprint INFRA-VALIDACAO-ARTESANAL-HOLERITE -- prova de paridade ETL × Opus em contracheques

## Contexto

24 holerites estão no grafo (`data/output/grafo.sqlite`) — todos com paths corrigidos pela Sprint 98a. Aparentemente verde. **Mas**: layouts G4F vs Infobase divergem substancialmente (G4F é empregador atual via contrato federal MEC, Infobase foi o anterior; ambos coexistem no histórico). Auditoria nunca confrontou os campos extraídos pelo `src/extractors/contracheque_pdf.py` com leitura humana via Opus multimodal. O risco: `liquido` correto por acaso (igual ao valor depositado em banco) mas `base_inss` ou `irrf_retido` errados — impacto direto no IRPF.

Esta sprint estabelece o gabarito artesanal: 2 amostras (1 de cada empregador), comparando ETL vs Opus campo-a-campo, especialmente nos campos que viram tag IRPF (`pagador`, `fonte_renda`, `imposto_pago`).

## Objetivo

1. Selecionar 2 amostras: 1 holerite G4F + 1 holerite Infobase.
2. Para cada amostra:
   - Capturar dict ETL via `from src.extractors.contracheque_pdf import extrair` (ou nome canônico atual).
   - Capturar dict Opus via Read multimodal sobre PDF (Opus = eu).
   - Persistir em `data/output/opus_ocr_cache/<sha256>.json` no schema canônico estendido (após INFRA-OPUS-SCHEMA-EXTENDIDO).
   - Diff campo-a-campo, com atenção aos campos fiscais críticos.
   - Marcar CSV `data/output/validacao_arquivos.csv`.
3. Relatório `docs/auditorias/VALIDACAO_ARTESANAL_HOLERITE_2026-MM-DD.md`.
4. Veredito. Se REPROVADO → sprint-filha em backlog.

## Validação ANTES (grep -- padrão (k))

```bash
ls data/raw/andre/holerites/ | head -5
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='documento' AND json_extract(metadata,'\$.tipo_documento') LIKE '%holerite%'"
# esperado: 24
grep -rn "G4F\|INFOBASE" mappings/fornecedores*.yaml | head
.venv/bin/python -c "from src.extractors.contracheque_pdf import extrair; print('importa OK')"
```

Confirma: (a) há 24 holerites no grafo, (b) fornecedores G4F e INFOBASE estão mapeados, (c) extrator importa.

## Não-objetivos (padrão (t))

- **NÃO** validar mais de 2 amostras nesta sprint.
- **NÃO** corrigir extrator se reprovar — sprint-filha cuida.
- **NÃO** redactar PII (CPF do Andre) em log INFO; mascarar no relatório (`XXX.XXX.XXX-XX`).
- **NÃO** processar holerites da Vitória (escopo é só Andre nesta rodada; Vitória será sprint análoga futura).
- **NÃO** mexer em `mappings/pessoas.yaml` (PII; dono aprova).
- **NÃO** persistir o PDF inteiro em qualquer cache — só os campos extraídos.

## Spec de implementação

Mesmo loop canônico de 7 passos da Sprint INFRA-VALIDACAO-ARTESANAL-CUPOM, adaptado:

### Diferença 1 — Schema estendido (holerite)

`dict_opus` deve preencher os campos opcionais do bloco `holerite` definido em INFRA-OPUS-SCHEMA-EXTENDIDO:

```python
dict_opus_holerite = {
    "sha256": "...",
    "tipo_documento": "holerite",
    "estabelecimento": {"razao_social": "G4F SOLUCOES CORPORATIVAS LTDA", "cnpj": "..."},
    "data_emissao": "2026-MM-DD",
    "competencia": "2026-MM",
    "empresa": {"cnpj": "...", "razao_social": "G4F..."},
    "funcionario": {"cpf_mascarado": "XXX.XXX.XXX-XX", "nome": "Andre da Silva Batista de Farias"},
    "salario_base": ...,
    "proventos": [
        {"codigo": "001", "descricao": "Salario base", "referencia": "30/30", "valor": ...},
        {"codigo": "...", "descricao": "Adicional...", "valor": ...},
    ],
    "descontos": [
        {"codigo": "...", "descricao": "INSS", "valor": ...},
        {"codigo": "...", "descricao": "IRRF", "valor": ...},
    ],
    "base_inss": ...,
    "base_irrf": ...,
    "liquido": ...,
    "extraido_via": "opus_v4_7_artesanal",
    "confianca_global": 0.97,
    "ts_extraido": "..."
}
```

### Diferença 2 — Campos críticos da classe A

Para holerite, **classe A inclui**: `cnpj` empresa, `competencia`, `liquido`, **`base_inss`**, **`base_irrf`**, **soma proventos**, **soma descontos**. (Os dois últimos: classe A porque desvio aritmético invalida a coerência da folha.)

### Diferença 3 — Sub-grupo G4F vs Infobase

Marcar no relatório qual empregador cada amostra refere. Padrão: 1 G4F (folha mais recente) + 1 Infobase (folha de 2025 ou anterior). Justificativa: cobre os 2 layouts existentes — gate 4-way agora cobre o universo real, não só uma amostra de cada.

### Diferença 4 — Verificação contra extrato bancário

Como camada extra de defesa em camadas (padrão `(n)`): após dict_opus pronto, conferir `liquido` contra o lançamento correspondente no `extrato` do XLSX (`data/output/ouroboros_2026.xlsx` aba extrato, mês = `competencia` + 1). Diferença ≥ R$ 0,01 → flag adicional no relatório.

```python
import pandas as pd
df = pd.read_excel("data/output/ouroboros_2026.xlsx", sheet_name="extrato")
mes_pagamento = ...  # competencia + 1
candidatos = df[(df["mes_ref"] == mes_pagamento) & (df["categoria"] == "Salário") & (df["quem"] == "Andre")]
batimento = abs(candidatos["valor"].max() - dict_opus_holerite["liquido"]) <= 0.01
```

## Proof-of-work (padrão (u))

```bash
# 1. Listar holerites de Andre
ls data/raw/andre/holerites/ | sort

# 2. Para cada amostra: rodar extrator
.venv/bin/python -c "from src.extractors.contracheque_pdf import extrair; from pathlib import Path; r = extrair(Path('data/raw/andre/holerites/<G4F>.pdf')); print(r)"

# 3. Confirmar batimento com extrato bancário
.venv/bin/python -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
salarios = df[(df['categoria']=='Salario') & (df['quem']=='Andre')].sort_values('data')
print(salarios[['data','valor','mes_ref']].head(24))
"

# 4. Cache populado
ls data/output/opus_ocr_cache/ | wc -l
# Esperado: cresce >= 2 (1 G4F + 1 Infobase)

# 5. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/ -k "holerite or contracheque" -q
```

## Critério de aceitação (gate (z))

1. 2 amostras processadas (1 G4F + 1 Infobase).
2. Cache cresce ≥ 2 entradas para tipo `holerite`.
3. Relatório existe com side-by-side ETL × Opus + bloco "Batimento com extrato" mostrando R$ 0,00 diferença para amostra 1 e amostra 2.
4. CSV marcado para campos críticos: `competencia`, `liquido`, `base_inss`, `base_irrf`, `cnpj_empresa`.
5. Veredito declarado.
6. Se REPROVADO: sprint-filha (`sprint_holerite_fix_*.md`).
7. PII corretamente mascarada (zero CPF/CNPJ pessoal nos logs INFO da sessão).
8. Gauntlet verde.

## Referência

- Extrator: `src/extractors/contracheque_pdf.py` (ou nome canônico atual via `grep -r contracheque src/`).
- Sprint-pai schema: INFRA-OPUS-SCHEMA-EXTENDIDO.
- Sprint 98a (paths corrigidos): commit `6228c91`.
- AUDIT2-RAZAO-SOCIAL-HOLERITE: backlog ainda aberto — pode interagir com esta validação.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase A1.

*"O holerite é o documento mais privado entre todos; validar sem mascarar é falha de respeito." — princípio INFRA-VALIDACAO-ARTESANAL-HOLERITE*
