# ADR-01: Python + pandas para ETL financeiro

## Status: Aceita

## Contexto

O pipeline precisa processar múltiplos formatos de entrada: CSV (Nubank, C6), XLSX e XLS (C6 encriptado, histórico), PDF protegido (Itaú, Santander) e imagens (screenshots de conta de energia). Cada banco tem formato próprio, sem padrão entre eles.

A escolha da linguagem precisava atender: riqueza de bibliotecas de parsing, facilidade de prototipagem rápida (projeto pessoal, não equipe), e ecossistema de dados maduros.

## Decisão

Usar Python 3.10+ com pandas como engine de manipulação tabular. Cada formato tem sua biblioteca especializada (pdfplumber para PDF, xlrd para XLS, openpyxl para XLSX, tesseract para OCR), todas com bindings Python maduros.

pandas foi escolhido sobre alternativas (polars, dask) pela familiaridade, documentação abundante e por ser suficiente para o volume de dados (~3.000 transações/ano).

## Consequências

**Positivas:**
- Biblioteca disponível para cada formato encontrado, sem necessidade de parsers customizados
- Prototipagem rápida: extrator novo em ~50 linhas
- Ecossistema pandas/openpyxl permite leitura e escrita de XLSX com formatação
- Comunidade ampla para debug de edge cases (PDFs mal formados, encodings)

**Negativas:**
- Performance não é crítica para o volume atual, mas pandas tem overhead de memória para DataFrames pequenos
- Dependência de bibliotecas com manutenção variável (xlrd parou de suportar XLSX, msoffcrypto-tool tem poucos mantenedores)
- Python não é ideal para distribuição como binário (usuário precisa de ambiente Python configurado)

---

*"A perfeição é alcançada não quando não há mais nada a adicionar, mas quando não há mais nada a remover." -- Antoine de Saint-Exupéry*
