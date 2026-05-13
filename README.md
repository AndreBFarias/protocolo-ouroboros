<div align="center">

<img src="assets/icon.png" width="120" alt="Protocolo Ouroboros">

# Protocolo Ouroboros

Pipeline ETL financeiro pessoal com dashboard interativo e integração Obsidian.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?style=flat&logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75?style=flat&logo=plotly&logoColor=white)
[![CI](https://github.com/AndreBFarias/protocolo-ouroboros/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreBFarias/protocolo-ouroboros/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/Licen%C3%A7a-GPLv3-blue?style=flat)
![Status](https://img.shields.io/badge/Status-Produ%C3%A7%C3%A3o-brightgreen?style=flat)

</div>

---

### Quick Start

```bash
git clone git@github.com:[REDACTED]/protocolo-ouroboros.git
cd protocolo-ouroboros
./install.sh
./run.sh
```

O menu interativo guia todas as operações: processamento, dashboard, relatórios, integração Obsidian e validação.

---

### Para colaboradores AI (Claude, Codex, Cursor, etc.)

Se você é uma sessão de modelo de linguagem trabalhando no projeto, **leia `CLAUDE.md` na raiz primeiro**. Ele declara os 3 documentos canônicos que devem ser lidos antes de criar qualquer sprint, a filosofia central (ciclo de graduação Opus -> ETL), as ferramentas (`scripts/dossie_tipo.py`) e as regras invioláveis (acentuação PT-BR, zero emojis, zero menções a IA).

O projeto se autogerencia via dossiês por tipo documental. Toda spec que toca extrator/ingestor/linker de um tipo segue o ritual artesanal de 6 fases descrito em `docs/CICLO_GRADUACAO_OPERACIONAL.md`.

---

### Sobre

Consolida dados bancários de múltiplas fontes (CSVs, XLSX, XLS, PDFs protegidos, imagens via OCR) em um XLSX unificado com 8 abas, relatórios mensais em Markdown e dashboard Streamlit com visualizações interativas.

| Transações | Meses | Bancos | Regras | Overrides | Tags IRPF |
|:----------:|:-----:|:------:|:------:|:---------:|:---------:|
| 6.094 | 82 | 6 | 111 | 10 | 164 |

---

### Arquitetura

```mermaid
flowchart LR
    subgraph Entrada
        A[CSVs] --> E[Extratores]
        B[PDFs] --> E
        C[XLSX/XLS] --> E
        D[OCR] --> E
    end

    subgraph Pipeline
        E --> F[Normalização]
        F --> G[Deduplicação]
        G --> H[Categorização]
        H --> I[IRPF Tagger]
    end

    subgraph Saída
        I --> J[XLSX 8 abas]
        I --> K[Relatórios MD]
        I --> L[Dashboard]
        I --> M[Obsidian]
    end
```

---

### Funcionalidades

| Categoria | Funcionalidade |
|-----------|---------------|
| Extração | 22 extratores: 9 bancários (Nubank cartão/CC, C6 CC/cartão, Itaú, Santander, OFX Nubank PF/PJ, energia OCR) + 13 documentais (NFCe, DANFE, XML NFe, boleto, cupom térmico foto, cupom garantia estendida, receita médica, garantia fabricante, recibo não-fiscal, DAS PARCSN, DIRPF, contracheque, garantia fabricante) |
| Detecção | Identifica banco, tipo, pessoa (CPF+CNPJ+razão social+alias) e período pelo conteúdo do arquivo |
| Categorização | 111 regras regex + 10 overrides manuais + categorias_item.yaml + categorizer.delete-before-insert idempotente (100% de cobertura) |
| Deduplicação | 3 níveis: UUID, hash cross-source, pares de transferência + canonicalizer variantes curtas (Sprint 82) + dedupe de roteamento por SHA-256 (Sprint P2.3) |
| IRPF | 22 regras declarativas em `mappings/irpf_regras.yaml` (5 tipos fiscais) + 75/164 tags com CNPJ/CPF |
| Dashboard | 13 páginas interativas com tema Dracula (Visão Geral, Categorias, Extrato, Contas, Pagamentos, Projeções, Metas, Análise, IRPF, Catalogação, Busca Global, Grafo + Obsidian, Completude) |
| Relatórios | Mensais em Markdown com diagnóstico comparativo (variação vs mês-1 e média móvel) + resumo narrativo heurístico PT-BR + alertas de anomalia |
| Grafo de conhecimento | SQLite 7.480 nodes / 24.700 edges. 41 documentos catalogados: 24 holerites + 10 DAS + 4 NFCe + 2 boletos + 1 DIRPF |
| Validação | Gauntlet `make lint` + pytest (1.971 passed) + `make smoke` (23 checagens + 8 contratos aritméticos) + `scripts/auditar_extratores.py` |
| Obsidian | Sincronização bidirecional com vault `Controle de Bordo` (forbidden zones ADR-18; soberania humana via tag + frontmatter) |
| OCR | Leitura de contas de energia via Tesseract (valores R$ 100% precisos) |

---

### Uso

**Menu interativo:**

```bash
./run.sh
```

**Comandos diretos:**

```bash
./run.sh --tudo            # Processa todos os dados
./run.sh --mes 2026-04     # Processa um mês específico
./run.sh --inbox           # Processa arquivos do inbox
./run.sh --dashboard       # Abre o dashboard Streamlit
./run.sh --relatorio       # Gera relatório do mês atual
./run.sh --sync            # Sincroniza com Obsidian
./run.sh --check           # Health check
./run.sh --irpf 2026       # Gera pacote IRPF
./run.sh --gauntlet        # Executa gauntlet de testes
```

**Via Makefile:**

```bash
make help        # Lista todos os comandos
make install     # Setup completo
make process     # Pipeline completo
make dashboard   # Abre dashboard Streamlit
make lint        # Verifica código (ruff)
make gauntlet    # Executa gauntlet de testes
```

---

### Estrutura do Projeto

```
protocolo-ouroboros/
├── run.sh                        # Entrypoint CLI com menu interativo
├── install.sh                    # Setup completo (venv + deps + tesseract)
├── Makefile                      # Targets automatizados
├── assets/
│   └── icon.png                  # Logo do projeto
│
├── src/
│   ├── pipeline.py               # Orquestrador principal (11 passos)
│   ├── inbox_processor.py        # Detecção, renomeação e organização
│   ├── extractors/               # 22 extratores (9 bancários + 13 documentais)
│   ├── transform/                # Categorização, deduplicação, IRPF
│   ├── load/                     # XLSX writer + relatórios MD
│   ├── projections/              # Cenários financeiros
│   ├── dashboard/                # Streamlit app (6 páginas, tema Dracula)
│   ├── obsidian/                 # Sincronização com vault
│   └── utils/                    # Logger, PDF reader, validador
│
├── mappings/                     # Regras YAML (categorias, overrides, metas)
├── data/                         # Dados financeiros (no .gitignore)
├── docs/                         # Arquitetura, ADRs, sprints, armadilhas
└── scripts/                      # Gauntlet de testes e pre-commit
```

<!-- Screenshots do dashboard aqui -->

---

### Tecnologias

| Tecnologia | Uso |
|-----------|-----|
| Python 3.11+ | Linguagem principal |
| pandas | Manipulação de dados tabulares |
| pdfplumber | Extração de texto de PDFs |
| openpyxl | Leitura/escrita de XLSX |
| xlrd + msoffcrypto-tool | Leitura de XLS encriptados |
| Tesseract OCR | Leitura de imagens (contas de energia) |
| Streamlit | Dashboard interativo |
| Plotly | Gráficos e visualizações |
| rich | Logging formatado no terminal |
| PyYAML | Configuração de regras |
| ruff | Linting e formatação |

---

### Documentação

| Documento | Descrição |
|-----------|-----------|
| [CLAUDE.md](CLAUDE.md) | Instruções completas para agentes de IA |
| [GSD.md](GSD.md) | Onboarding rápido (Get Stuff Done) |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Diagrama de fluxo e componentes |
| [ARMADILHAS.md](docs/ARMADILHAS.md) | Bugs críticos e soluções |
| [AUDITORIA_SPRINTS.md](docs/AUDITORIA_SPRINTS.md) | Auditoria de cada sprint |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de mudanças |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Guia de contribuição |
| [DADOS_FALTANTES.md](DADOS_FALTANTES.md) | Checklist de dados pendentes |

---

### Licença

Distribuído sob a licença GPLv3. Veja [LICENSE](LICENSE) para detalhes.

---

<div align="center">

*"A frugalidade inclui todas as outras virtudes." -- Cícero*

</div>
