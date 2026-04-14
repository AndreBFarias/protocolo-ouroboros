# Arquitetura -- Protocolo Ouroboros

## Visão Geral

Pipeline ETL financeiro pessoal que processa arquivos brutos (PDFs, CSVs, XLSX, XLS, imagens) de múltiplos bancos, extrai transações, categoriza automaticamente, deduplica entre fontes e gera saída consolidada em XLSX, relatórios Markdown e dashboard interativo.

O sistema segue o princípio **Local First**: tudo funciona offline, sem dependência de APIs pagas ou serviços cloud.

---

## Fluxo de Dados

```
inbox/                           Ponto de entrada do usuário
  |                              (arrasta arquivos brutos aqui)
  v
inbox_processor                  Detecta banco/pessoa pelo conteúdo,
  |                              move para pasta correta
  v
data/raw/{pessoa}/{banco}/       Arquivos organizados por pessoa e banco
  |
  v
src/extractors/ (7 extratores)   Um extrator por banco/formato:
  |                                nubank_cartao (CSV)
  |                                nubank_cc (CSV)
  |                                c6_cc (XLS encriptado)
  |                                c6_cartao (CSV)
  |                                itau_pdf (PDF protegido)
  |                                santander_pdf (PDF)
  |                                energia_ocr (imagem -> tesseract)
  v
src/transform/normalizer         Padroniza schema: Transacao dataclass
  |                              com 9 campos obrigatórios
  v
src/transform/deduplicator       3 níveis de deduplicação:
  |                                1. UUID (Nubank CC)
  |                                2. Hash cross-source
  |                                3. Pares de transferência
  v
src/transform/categorizer        111 regras regex (mappings/categorias.yaml)
  |                              + 10 overrides manuais (mappings/overrides.yaml)
  |                              Atribui: categoria, classificação, quem
  v
src/transform/irpf_tagger        21 regras, 5 tipos de tag:
  |                                rendimento_tributavel, inss, irrf,
  |                                despesa_medica, imposto_pago
  v
src/load/xlsx_writer             Gera XLSX com 8 abas:
  |                                extrato, renda, dividas_ativas,
  |                                inventario, prazos, resumo_mensal,
  |                                irpf, analise
  |
src/load/relatorio               Gera relatório Markdown mensal
  |                              com resumo, top categorias, alertas,
  |                              comparativo e projeção
  v
data/output/                     XLSX final + relatórios MD (44 meses)
  |
  v
src/obsidian/sync                Sincroniza relatórios para vault Obsidian
  |                              ~/Controle de Bordo/Pessoal/Financeiro/
  |                              Frontmatter YAML + Dataview queries
  v
src/dashboard/ (Streamlit)       6 páginas interativas:
                                   visao_geral, categorias, extrato,
                                   contas, projecoes, metas
```

---

## Camadas

### 1. Extração (`src/extractors/`)

Cada extrator implementa a interface base: recebe caminho do arquivo, retorna lista de `Transacao`.

| Extrator | Formato | Biblioteca | Particularidades |
|----------|---------|------------|------------------|
| `nubank_cartao` | CSV | pandas | Colunas: date, title, amount |
| `nubank_cc` | CSV | pandas | Colunas: Data, Valor, Identificador, Descricao. UUID para dedup |
| `c6_cc` | XLS | msoffcrypto-tool + xlrd | Arquivo encriptado, decripta antes de ler |
| `c6_cartao` | CSV | pandas | Formato padrão C6 |
| `itau_pdf` | PDF | pdfplumber | Protegido com senha 051273 |
| `santander_pdf` | PDF | pdfplumber | Cartão Elite Visa (Black Way = 7342) |
| `energia_ocr` | Imagem | tesseract + Pillow | Valores R$ OK, consumo kWh parcial (67%) |

### 2. Transformação (`src/transform/`)

- **normalizer.py**: Converte saída dos extratores para schema padrão `Transacao`.
- **deduplicator.py**: Elimina duplicatas em 3 níveis (UUID, hash, pares).
- **categorizer.py**: Aplica 111 regras regex + 10 overrides. Overrides têm prioridade. Detecta padrões novos não categorizados.
- **irpf_tagger.py**: Marca transações relevantes para IRPF com tag e tipo.
- **validator.py**: 6 checagens de integridade pós-processamento.

### 3. Carga (`src/load/`)

- **xlsx_writer.py**: Gera XLSX com 8 abas seguindo schema definido. Formatação de colunas, tipos e validação.
- **relatorio.py**: Gera Markdown mensal com resumo financeiro, top categorias, comparativo, alertas, transferências internas, IRPF acumulado e projeção.

### 4. Apresentação

- **src/dashboard/**: Streamlit com 6 páginas, sidebar com filtros globais (mês, pessoa), tema dark, gráficos Plotly.
- **src/obsidian/sync.py**: Sincroniza relatórios para vault Obsidian com frontmatter YAML e Dataview queries.

---

## Dependências entre Módulos

```
pipeline.py (orquestrador)
  |
  +-- inbox_processor.py
  |
  +-- extractors/*
  |     +-- base.py (dataclass Transacao)
  |
  +-- transform/normalizer.py
  |     +-- base.py
  |
  +-- transform/deduplicator.py
  |     +-- base.py
  |
  +-- transform/categorizer.py
  |     +-- mappings/categorias.yaml
  |     +-- mappings/overrides.yaml
  |
  +-- transform/irpf_tagger.py
  |
  +-- transform/validator.py
  |
  +-- load/xlsx_writer.py
  |     +-- base.py
  |
  +-- load/relatorio.py
  |
  +-- obsidian/sync.py
       +-- load/relatorio.py (reutiliza dados)
```

---

## Stack Tecnológico

| Componente | Versão | Uso |
|------------|--------|-----|
| Python | 3.10+ | Runtime |
| pandas | >= 2.0 | Manipulação de dados tabulares |
| pdfplumber | >= 0.10 | Extração de texto de PDFs |
| openpyxl | >= 3.1 | Leitura/escrita de XLSX |
| xlrd | >= 2.0 | Leitura de XLS legado (C6) |
| msoffcrypto-tool | >= 5.0 | Decriptação de XLS encriptado (C6) |
| streamlit | >= 1.30 | Dashboard interativo |
| plotly | >= 5.18 | Gráficos interativos |
| tesseract-ocr | >= 4.0 | OCR para screenshots de energia |
| pytesseract | >= 0.3 | Binding Python para tesseract |
| Pillow | >= 10.0 | Manipulação de imagens para OCR |
| rich | >= 13.0 | Logging formatado no terminal |
| pyyaml | >= 6.0 | Leitura de mapeamentos YAML |

---

*"A arquitetura deve revelar a intenção." -- Robert C. Martin*
