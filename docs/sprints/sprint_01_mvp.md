# Sprint 01 -- MVP: Pipeline ETL Financeiro

## Status: Concluída
Data de conclusão: 2026-04-14
Commit: 10b4b64
Issue: #1

## Objetivo

Pipeline ETL financeiro mínimo viável. Processar extratos bancários de múltiplos bancos, categorizar transações, deduplicar e gerar saída consolidada em XLSX e relatório Markdown.

## Entregas

- [x] Scaffold completo (estrutura de pastas, pyproject.toml, install.sh, run.sh)
- [x] .gitignore e .env configurados
- [x] Inbox processor inteligente (detecta banco/tipo/pessoa, renomeia, move)
- [x] File detector (identificação automática de formato e origem)
- [x] Extrator Nubank CSV - formato cartão de crédito
- [x] Extrator Nubank CSV - formato conta corrente
- [x] Extrator C6 XLSX - conta corrente
- [x] Extrator C6 XLS - fatura cartão
- [x] Extrator Itaú PDF - extrato protegido por senha
- [x] Extrator Santander PDF - fatura cartão Black Way
- [x] Categorizador regex base (mappings iniciais por padrão de descrição)
- [x] Deduplicador 3 níveis (UUID + hash + detecção de pares de transferência)
- [x] Normalizador de transações
- [x] XLSX writer (gera planilha com 8 abas)
- [x] Relatório MD mensal (resumo textual por mês)
- [x] Importação de histórico do XLSX antigo (migração de dados legados)
- [x] Logger configurado com Rich
- [x] PDF reader com suporte a senhas

## O que ficou faltando

- Extrator CAESB (água): não havia arquivo de referência disponível
- Parser de boleto genérico: escopo demasiado amplo para o MVP
- Testes automatizados: priorizou-se funcionalidade sobre cobertura de testes

## Armadilhas conhecidas

- C6 XLS precisa de msoffcrypto para descriptografia
- Itaú PDF protegido com senha [SENHA]
- Nubank tem 2 formatos distintos (cartão vs conta corrente)
- Histórico antigo tem colunas diferentes do schema novo

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `pyproject.toml` | Configuração do projeto e dependências |
| `install.sh` | Script de setup do ambiente |
| `run.sh` | Entrypoint principal do pipeline |
| `.gitignore` | Proteção de dados financeiros e artefatos |
| `src/pipeline.py` | Orquestrador principal do ETL |
| `src/extractors/nubank_cartao.py` | Extrator de fatura Nubank cartão |
| `src/extractors/nubank_cc.py` | Extrator de extrato Nubank conta corrente |
| `src/extractors/c6_cc.py` | Extrator de extrato C6 conta corrente |
| `src/extractors/c6_cartao.py` | Extrator de fatura C6 cartão |
| `src/extractors/itau_pdf.py` | Extrator de extrato Itaú PDF |
| `src/extractors/santander_pdf.py` | Extrator de fatura Santander PDF |
| `src/transform/categorizer.py` | Categorizador regex base |
| `src/transform/deduplicator.py` | Deduplicador 3 níveis |
| `src/transform/normalizer.py` | Normalizador de transações |
| `src/load/xlsx_writer.py` | Gerador de XLSX com 8 abas |
| `src/load/relatorio.py` | Gerador de relatório Markdown |
| `src/utils/logger.py` | Logger com Rich |
| `src/utils/pdf_reader.py` | Leitor de PDFs com suporte a senha |
| `src/inbox_processor.py` | Processador de inbox |
| `src/file_detector.py` | Detector de formato/origem de arquivos |

## Critério de sucesso

`./run.sh --tudo` roda sem erros, gera XLSX consolidado + relatório Markdown mensal a partir dos extratos no inbox.

## Dependências

Nenhuma. Sprint fundacional.
