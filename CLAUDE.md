# CLAUDE.md — Controle de Bordo

```
STATUS: BOOTSTRAP | LANG: PT-BR
```

---

## MISSÃO

Pipeline ETL financeiro pessoal. Input: arquivos brutos (PDFs, CSVs, XLSX, imagens). Output: XLSX consolidado com todas as abas + dashboard Streamlit + análise mensal.

**Você (Opus) toma TODAS as decisões técnicas.** Ao receber arquivos novos em `data/raw/`, você:
1. Lê cada arquivo pra entender formato, estrutura, banco de origem
2. Extrai as transações
3. Categoriza automaticamente
4. Cruza entre fontes (evita contagem dupla)
5. Gera o XLSX final atualizado
6. Gera análise em markdown com insights

**Não pergunte o que fazer. Leia os dados e decida.**

---

## SENHAS

PDFs bancários geralmente protegidos. Tentar nesta ordem:
1. `051273`
2. `05127`
3. `05127373122` (CPF completo sem pontos)
4. Se nenhuma funcionar: perguntar ao usuário

---

## ESTRUTURA

```
controle-de-bordo/
├── CLAUDE.md
├── pyproject.toml
├── install.sh
├── run.sh                       # Entrypoint: ./run.sh --mes YYYY-MM
├── data/
│   ├── raw/YYYY-MM/             # Usuário joga arquivos brutos aqui
│   ├── processed/               # CSVs intermediários padronizados
│   ├── output/                  # XLSX final + relatórios MD
│   └── historico/               # XLSX antigo pra importar
├── src/
│   ├── pipeline.py              # Orquestrador principal
│   ├── extractors/              # Um extractor por banco/fonte
│   ├── transform/               # Categorização, normalização, dedup
│   ├── load/                    # XLSX writer, relatório MD
│   ├── dashboard/               # Streamlit app
│   └── utils/                   # PDF reader, OCR, helpers
├── mappings/                    # YAML com regras de categorização
└── tests/
```

---

## COMO IDENTIFICAR CADA ARQUIVO

O Opus deve ler o conteúdo (não confiar só no nome) pra detectar:

| Pista no conteúdo | Banco/Fonte |
|-------------------|-------------|
| "ITAÚ UNIBANCO", "itau.com.br", agência 6450 | Itaú - extrato CC |
| "SANTANDER", "4220 XXXX XXXX 7342" | Santander - fatura cartão |
| "NU PAGAMENTOS", "NUBANK", "Nu Financeira" | Nubank |
| "BCO C6 S.A.", "31.872.495" | C6 Bank |
| "CAIXA ECONOMICA" | Caixa |
| "Neoenergia", "CEB", "Kwh" | Conta de energia |
| "CAESB", "Saneamento" | Conta de água |
| CSV com colunas: date, title, amount | Nubank CSV padrão |
| CSV com colunas: Data, Histórico, Valor | C6 CSV padrão |
| Imagem com "Faturas e Consumo" | Screenshot energia (OCR) |

**Se não reconhecer:** loga warning e pula. Nunca inventar dados.

---

## SCHEMA DO XLSX

### Aba: extrato

Tabela principal. Cada linha = uma transação.

| Coluna | Tipo | Obrigatório |
|--------|------|-------------|
| data | date | sim |
| valor | float | sim |
| forma_pagamento | str (Pix/Débito/Crédito/Boleto/Transferência) | sim |
| local | str (nome estabelecimento) | sim |
| quem | str (André/Vitória/Casal) | sim |
| categoria | str (ver lista) | sim |
| classificacao | str (Obrigatório/Questionável/Supérfluo) | sim |
| banco_origem | str | sim |
| tipo | str (Despesa/Receita/Transferência Interna/Imposto) | sim |
| mes_ref | str (YYYY-MM) | sim |
| tag_irpf | str ou null | não |
| obs | str | não |

### Aba: renda

Uma linha por mês por fonte de renda.

| Coluna | Tipo |
|--------|------|
| mes_ref | str (YYYY-MM) |
| fonte | str (G4F/Infobase/PJ Vitória/Rendimentos) |
| bruto | float |
| inss | float |
| irrf | float |
| vr_va | float |
| liquido | float |
| banco | str |

### Aba: dividas_ativas

Snapshot mensal de todas as contas fixas e dívidas.

| Coluna | Tipo |
|--------|------|
| mes_ref | str |
| custo | str |
| valor | float |
| status | str (Pago/Não Pago/Parcial) |
| vencimento | int (dia do mês) |
| quem | str |
| recorrente | bool |
| obs | str |

### Aba: inventario

Bens do casal com depreciação.

| Coluna | Tipo |
|--------|------|
| bem | str |
| valor_aquisicao | float |
| vida_util_anos | int |
| depreciacao_anual | float |
| perda_mensal | float |

### Aba: prazos

Vencimentos recorrentes.

| Coluna | Tipo |
|--------|------|
| conta | str |
| dia_vencimento | int |
| banco_pagamento | str |
| auto_debito | bool |

### Aba: resumo_mensal

Gerada automaticamente pelo pipeline.

| Coluna | Tipo |
|--------|------|
| mes_ref | str |
| receita_total | float |
| despesa_total | float |
| saldo | float |
| top_categoria | str |
| top_gasto | str |
| total_obrigatorio | float |
| total_superfluo | float |
| total_questionavel | float |

### Aba: irpf

Dados relevantes pro imposto de renda, acumulados.

| Coluna | Tipo |
|--------|------|
| ano | int |
| tipo | str (rendimento_tributavel/inss/irrf/despesa_medica/isento/imposto_pago) |
| fonte | str |
| cnpj_cpf | str |
| valor | float |
| mes | str |

### Aba: analise

Gerada pelo Opus. Texto livre com insights do mês.

---

## CATEGORIZAÇÃO AUTOMÁTICA

O Opus deve construir e refinar o mapeamento regex → categoria ao ler os dados reais. Ponto de partida:

```yaml
delivery:
  regex: "IFD\\*|IFOOD|RAPPI|ZDELIVERY|UBER.*EATS"
  classificacao: Questionável

transporte:
  regex: "UBER|99POP|99APP|TAXI|CABIFY"
  classificacao: Questionável

salario:
  regex: "PAGTO.*SALARIO|CREDITO.*SALARIO"
  tipo: Receita

transferencia_casal:
  regex: "Vit[oó]ria|VITORIA"
  tipo: Transferência Interna

energia:
  regex: "NEOENERGIA|CEB|ENERGETICA"
  classificacao: Obrigatório

agua:
  regex: "CAESB|SANEAMENTO|COMPANHIA D"
  classificacao: Obrigatório

farmacia:
  regex: "DROGARIA|FARMACIA|DROGA.RAIA|PAGUE.MENOS"
  categoria: Remédios
  classificacao: Obrigatório

saude_dedutivel:
  regex: "CLINICA|HOSPITAL|CONSULT|PSIQ|PSICOL|SESC.*SERVICO"
  classificacao: Obrigatório
  tag_irpf: dedutivel_medico

imposto:
  regex: "RECEITA.FED|DARF|DAS.MEI"
  tipo: Imposto
  tag_irpf: imposto_pago

pagamento_cartao:
  regex: "NU.PAGAMENT|BANCO.SANTA"
  tipo: Transferência Interna

pet:
  regex: "PET.CENTER|COBASI|PETZ"
  classificacao: Obrigatório

compras_online:
  regex: "SHOPEE|MERCADO.LIVRE|AMAZON|SHEIN"
  classificacao: Supérfluo

ia_ferramentas:
  regex: "XAI.LLC|OPENAI|ANTHROPIC|GOOGLE.CLOUD|CURSOR"
  classificacao: Questionável

natacao:
  regex: "SESC"
  classificacao: Obrigatório
```

**Regra de ouro:** se não reconhecer, marca como `Outros` + `Questionável`. Nunca inventar categoria. Se encontrar padrão novo recorrente, criar regex e documentar.

---

## DEDUPLICAÇÃO

Transferências entre contas próprias (pagar cartão, pix entre contas) NÃO são gastos. O Opus deve:
1. Identificar pares (saída de CC → entrada em cartão)
2. Marcar como `Transferência Interna`
3. Não contar no total de despesas

---

## DETECÇÃO DE QUEM (André vs Vitória)

- Transações de bancos/cartões do André → `André`
- Transações de bancos/cartões da Vitória → `Vitória`
- Se não der pra saber → `Casal`
- PIX pra Vitória = `Transferência Interna`, não gasto

---

## RUN.SH

```bash
#!/bin/bash
set -euo pipefail

MES=${1:-$(date +%Y-%m)}
VENV=".venv"

if [ ! -d "$VENV" ]; then
    echo "Rode ./install.sh primeiro"
    exit 1
fi

source "$VENV/bin/activate"

echo "=== Controle de Bordo — Processando $MES ==="

# 1. Processar arquivos brutos
python -m src.pipeline --mes "$MES"

# 2. Gerar XLSX
python -m src.load.xlsx_writer --mes "$MES"

# 3. Gerar relatório
python -m src.load.relatorio --mes "$MES"

echo ""
echo "=== Outputs ==="
echo "XLSX: data/output/controle_bordo_$(echo $MES | cut -d- -f1).xlsx"
echo "Relatório: data/output/$MES_relatorio.md"
echo ""
echo "Dashboard: ./run.sh --dashboard"

if [ "${1:-}" = "--dashboard" ]; then
    streamlit run src/dashboard/app.py
fi
```

---

## INSTALL.SH

```bash
#!/bin/bash
set -euo pipefail

echo "=== Controle de Bordo — Setup ==="

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install \
    pandas \
    openpyxl \
    pdfplumber \
    Pillow \
    pytesseract \
    pyyaml \
    streamlit \
    plotly \
    rich

# OCR (fallback pra screenshots)
sudo apt install -y tesseract-ocr tesseract-ocr-por 2>/dev/null || true

# Criar estrutura
mkdir -p data/{raw,processed,output,historico}
mkdir -p mappings

echo ""
echo "Setup completo."
echo "1. Jogue arquivos em data/raw/YYYY-MM/"
echo "2. Rode: ./run.sh YYYY-MM"
```

---

## ANÁLISE QUE O OPUS DEVE GERAR

Ao final do pipeline, gerar `data/output/YYYY-MM_relatorio.md` com:

1. **Resumo:** receita, despesa, saldo do mês
2. **Top 5 categorias** de gasto
3. **Comparativo** com mês anterior (se existir)
4. **Alertas:** gastos que subiram muito, contas não pagas, padrões preocupantes
5. **Transferências internas:** total movimentado entre contas (pra não confundir com gasto)
6. **IRPF:** total de rendimentos tributáveis e despesas dedutíveis acumulados no ano
7. **Projeção:** se continuar nesse ritmo, quanto sobra/falta no ano

---

## IMPORTAR HISTÓRICO

O XLSX antigo (`data/historico/controle_antigo.xlsx`) tem 1.254 lançamentos de ago/2022 a jul/2023. O Opus deve:
1. Ler a aba Extrato
2. Mapear pro schema novo (colunas extras ficam null)
3. Preservar categorias e classificações originais
4. Inserir na aba extrato do XLSX novo como dados históricos

---

## CONVENÇÕES

- PT-BR em tudo (código, comentários, outputs)
- Commits impessoais: `feat:`, `fix:`, `refactor:`
- Sem nomes pessoais em docstrings ou comentários
- Datas ISO 8601
- Valores float 2 casas decimais
- `data/` inteiro no .gitignore (dados financeiros nunca no repo)
- Sem hardcode de caminhos absolutos
- Logs via `rich` ou `logging`, nunca `print` em produção

---

## SPRINT 1 (MVP)

Ao receber este CLAUDE.md, o Opus deve:

1. Criar scaffold completo (todas as pastas, pyproject.toml, install.sh, run.sh)
2. Implementar extrator Itaú PDF (referência: `data/raw/` terá exemplos)
3. Implementar extrator Nubank CSV
4. Implementar categorizer com regex base
5. Implementar XLSX writer (gera as 8 abas)
6. Importar histórico do XLSX antigo
7. Rodar com os dados de abril 2026 e gerar primeiro relatório

**Critério de sucesso:** `./run.sh 2026-04` roda sem erros e gera XLSX + relatório MD.
