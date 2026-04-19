# Extratores -- Índice gerado

Gerado automaticamente por `src/utils/doc_generator.py`. Não edite manualmente; atualize via `make docs`.

Os arquivos `.md` deste diretório (fora este) são curados à mão e descrevem o formato de cada fonte bancária.

## Cobertura

| Módulo | Classe principal | Doc curado |
|--------|------------------|------------|
| `c6_cartao` | `ExtratorC6Cartao` | [`c6_cartao.md`](c6_cartao.md) |
| `c6_cc` | `ExtratorC6CC` | [`c6_cc.md`](c6_cc.md) |
| `energia_ocr` | `ExtratorEnergiaOCR` | [`energia_neoenergia.md`](energia_neoenergia.md) |
| `itau_pdf` | `ExtratorItauPDF` | [`itau_cc.md`](itau_cc.md) |
| `nubank_cartao` | `ExtratorNubankCartao` | [`nubank_cartao.md`](nubank_cartao.md) |
| `nubank_cc` | `ExtratorNubankCC` | [`nubank_cc.md`](nubank_cc.md) |
| `ofx_parser` | `ExtratorOFX` | **ausente** |
| `santander_pdf` | `ExtratorSantanderPDF` | [`santander_cartao.md`](santander_cartao.md) |

## Descrição por módulo

### `c6_cartao`

Extrator de faturas de cartão C6 Bank (formato XLS criptografado).

**Classe principal:** `ExtratorC6Cartao`

**Docstring da classe:**

```
Extrai transações de XLS criptografados de fatura do cartão C6.

Formato: XLS protegido por senha com msoffcrypto.
Colunas: Data de compra, Nome no cartão, Final do Cartão, Categoria,
         Descrição, Parcela, Valor (em US$), Cotação (em R$), Valor (em R$)
```

Documentação detalhada: [`c6_cartao.md`](c6_cartao.md)

### `c6_cc`

Extrator de extrato de conta corrente C6 Bank (formato XLSX criptografado).

**Classe principal:** `ExtratorC6CC`

**Docstring da classe:**

```
Extrai transações do XLSX de conta corrente C6 Bank.

Arquivo criptografado com senha.
Colunas: Data Lançamento, Data Contábil, Título, Descrição,
         Entrada(R$), Saída(R$), Saldo do Dia(R$)
```

Documentação detalhada: [`c6_cc.md`](c6_cc.md)

### `energia_ocr`

Extrator de contas de energia (Neoenergia) via OCR de screenshots.

**Classe principal:** `ExtratorEnergiaOCR`

**Docstring da classe:**

```
Extrai dados de contas de energia via OCR de screenshots.
```

Documentação detalhada: [`energia_neoenergia.md`](energia_neoenergia.md)

### `itau_pdf`

Extrator de extratos bancários Itaú em PDF protegido por senha.

**Classe principal:** `ExtratorItauPDF`

**Docstring da classe:**

```
Extrai transações de PDFs de extrato Itaú protegidos por senha.

Formato: texto extraído via pdfplumber.
Cada linha de lançamento segue o padrão:
    DD/MM/YYYY <histórico> <valor com sinal>
Linhas de SALDO DO DIA são ignoradas.
```

Documentação detalhada: [`itau_cc.md`](itau_cc.md)

### `nubank_cartao`

Extrator de faturas de cartão de crédito Nubank (formato CSV: date,title,amount).

**Classe principal:** `ExtratorNubankCartao`

**Docstring da classe:**

```
Extrai transações de CSVs de fatura do cartão Nubank.

Formato esperado: date,title,amount
Usado por:
    - André: data/raw/andre/nubank_cartao/
    - Vitória PJ: data/raw/vitoria/nubank_pj_cartao/
```

Documentação detalhada: [`nubank_cartao.md`](nubank_cartao.md)

### `nubank_cc`

Extrator de extratos de conta corrente Nubank (CSV: Data,Valor,ID,Descrição).

**Classe principal:** `ExtratorNubankCC`

**Docstring da classe:**

```
Extrai transações de CSVs de conta corrente Nubank.

Formato esperado: Data,Valor,Identificador,Descrição
Usado por:
    - Vitória PF: data/raw/vitoria/nubank_pf_cc/
    - Vitória PJ: data/raw/vitoria/nubank_pj_cc/
```

Documentação detalhada: [`nubank_cc.md`](nubank_cc.md)

### `ofx_parser`

Extrator genérico de arquivos OFX (Open Financial Exchange).

Lê arquivos .ofx exportados por qualquer banco brasileiro (Itaú, Santander,
Nubank, C6, BB, Caixa) e converte para o schema padrão do Ouroboros.

**Classe principal:** `ExtratorOFX`

**Docstring da classe:**

```
Extrator genérico para arquivos OFX de qualquer banco.
```

_Sem documentação curada -- criar arquivo dedicado recomendado._

### `santander_pdf`

Extrator de faturas de cartão Santander (PDF sem senha).

Layout especial: PDFs com 2+ páginas de detalhamento possuem layout em
duas colunas (cartão principal esquerda, cartão adicional direita).
O pdfplumber concatena as colunas em cada linha, exigindo extração
via findall ao invés de match por linha.

**Classe principal:** `ExtratorSantanderPDF`

**Docstring da classe:**

```
Extrai transações de PDFs de fatura do cartão Santander.

Cartão SANTANDER ELITE VISA (sem senha).
Foco nas páginas de Detalhamento da Fatura.
```

Documentação detalhada: [`santander_cartao.md`](santander_cartao.md)
