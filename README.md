<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?style=flat&logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75?style=flat&logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/Licen%C3%A7a-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Produ%C3%A7%C3%A3o-brightgreen?style=flat)

# Controle de Bordo

Pipeline ETL financeiro pessoal com dashboard interativo e integração Obsidian.

</div>

---

### Sobre

Consolida dados bancários de múltiplas fontes (CSVs, XLSX, XLS, PDFs protegidos, imagens via OCR) em um XLSX unificado com 8 abas, relatórios mensais em Markdown e dashboard Streamlit com visualizações interativas.

---

### Funcionalidades

| Categoria | Funcionalidade |
|-----------|---------------|
| Extração | 7 extratores (Nubank, C6, Itaú, Santander, Neoenergia OCR) |
| Detecção | Identifica banco, tipo, pessoa e período pelo conteúdo do arquivo |
| Categorização | 111 regras regex + 10 overrides manuais (100% de cobertura) |
| Deduplicação | 3 níveis: UUID, hash cross-source, pares de transferência |
| IRPF | 21 regras de tagging automático em 5 tipos fiscais |
| Dashboard | 6 páginas interativas com Plotly (tema dark) |
| Relatórios | 44 relatórios mensais gerados automaticamente |
| Validação | 6 checagens de integridade do pipeline |
| Obsidian | Sincronização automática com vault pessoal |
| OCR | Leitura de contas de energia via Tesseract (valores R$ 100% precisos) |

---

### Instalação

```bash
git clone git@github.com:[REDACTED]/Financas.git
cd Financas
./install.sh
```

O script instala dependências Python no virtualenv, Tesseract OCR e cria a estrutura de diretórios.

---

### Uso

```bash
# Processar todos os dados
./run.sh --tudo

# Processar um mês específico
./run.sh --mes 2026-04

# Processar arquivos do inbox
./run.sh --inbox

# Abrir dashboard
./run.sh --dashboard

# Sincronizar com Obsidian
./run.sh --sync

# Health check
./run.sh --check
```

Ou via Makefile:

```bash
make help        # Lista todos os comandos
make install     # Setup completo
make process     # Pipeline completo
make dashboard   # Abre dashboard Streamlit
make lint        # Verifica código (ruff)
make validate    # Validação de integridade
```

---

### Estrutura do Projeto

```
Financas/
├── CLAUDE.md                     # Instruções para agentes de IA
├── GSD.md                        # Onboarding rápido (Get Stuff Done)
├── README.md                     # Este arquivo
├── pyproject.toml                # Dependências Python
├── Makefile                      # 13 targets automatizados
├── install.sh                    # Setup completo
├── run.sh                        # Entrypoint CLI
│
├── data/
│   ├── raw/{pessoa}/{banco}/     # Arquivos brutos por pessoa e banco
│   ├── processed/                # CSVs intermediários padronizados
│   ├── output/                   # XLSX final + relatórios Markdown
│   └── historico/                # Dados legados importados
│
├── src/
│   ├── pipeline.py               # Orquestrador principal (11 passos)
│   ├── inbox_processor.py        # Detecção, renomeação e organização
│   ├── extractors/               # 7 extratores bancários
│   │   ├── nubank_cartao.py      # CSV: date, title, amount
│   │   ├── nubank_cc.py          # CSV: Data, Valor, Identificador, Descrição
│   │   ├── c6_cc.py              # XLSX conta corrente
│   │   ├── c6_cartao.py          # XLS fatura (msoffcrypto + xlrd)
│   │   ├── itau_pdf.py           # PDF protegido (pdfplumber)
│   │   ├── santander_pdf.py      # PDF fatura cartão
│   │   └── energia_ocr.py        # Screenshot via Tesseract OCR
│   ├── transform/
│   │   ├── normalizer.py         # Padronização para schema único
│   │   ├── categorizer.py        # 111 regex + 10 overrides
│   │   ├── deduplicator.py       # UUID + hash + pares internos
│   │   └── irpf_tagger.py        # 21 regras de tagging fiscal
│   ├── load/
│   │   ├── xlsx_writer.py        # Geração do XLSX (8 abas)
│   │   └── relatorio.py          # Relatórios mensais Markdown
│   ├── projections/
│   │   └── scenarios.py          # Cenários financeiros
│   ├── dashboard/
│   │   ├── app.py                # Streamlit entrypoint
│   │   ├── dados.py              # Cache de dados
│   │   └── paginas/              # 6 páginas do dashboard
│   ├── obsidian/
│   │   └── sync.py               # Sincronização com vault
│   └── utils/
│       ├── logger.py             # Logging rotacionado (rich)
│       ├── file_detector.py      # Detecção de banco/tipo/pessoa
│       ├── pdf_reader.py         # Wrapper pdfplumber com senhas
│       └── validator.py          # 6 validações de integridade
│
├── mappings/
│   ├── categorias.yaml           # 111 regras regex
│   ├── overrides.yaml            # Correções manuais
│   ├── metas.yaml                # Metas financeiras
│   └── senhas.yaml               # Senhas e contas bancárias
│
├── docs/
│   ├── ARCHITECTURE.md           # Diagrama de fluxo ETL
│   ├── ARMADILHAS.md             # Bugs e aprendizados críticos
│   ├── AUDITORIA_SPRINTS.md      # Auditoria de cada sprint
│   ├── MODELOS.md                # Schemas de dados
│   ├── adr/                      # 7 Architecture Decision Records
│   ├── sprints/                  # 14 sprints documentadas
│   └── extractors/               # Auto-documentação de formatos
│
└── scripts/
    └── pre-commit-check.sh       # ruff + bloqueio de dados sensíveis
```

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

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para detalhes.

---

<div align="center">

*"A frugalidade inclui todas as outras virtudes." -- Cícero*

</div>
