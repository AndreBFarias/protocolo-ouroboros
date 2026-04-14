# Guia de Contribuição

## Como Contribuir

1. Faça um fork do repositório
2. Crie uma branch a partir de `main` (`git checkout -b feat/minha-feature`)
3. Implemente a mudança seguindo o estilo do projeto
4. Rode os checks locais: `make check`
5. Abra um Pull Request com descrição clara do que foi feito

---

## Requisitos

- Python 3.11+
- Dependências: `./install.sh`
- Ambiente virtual `.venv` obrigatório (nunca instalar global)
- Tesseract OCR para funcionalidades de leitura de imagem

---

## Estilo de Código

- **Linter/formatter:** `ruff` (configurado em `pyproject.toml`)
- **Idioma:** PT-BR em todo o código -- variáveis, funções, comentários, logs, outputs
- **Acentuação:** obrigatória e correta em todo texto em português
- **Zero emojis** em qualquer lugar do projeto (código, commits, docs, comentários)
- **Zero menções a ferramentas de IA** em qualquer arquivo ou commit
- **Type hints** em todas as funções
- **Logging** via `logging` ou `rich` -- nunca `print()` em produção
- **Paths:** sempre relativos via `pathlib.Path`
- **Limite:** 800 linhas por arquivo (exceto configs e testes)

---

## Commits

Formato obrigatório:

```
tipo: descrição imperativa em PT-BR
```

Tipos válidos: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `chore`

Exemplos:
- `feat: adicionar extrator de fatura Santander`
- `fix: corrigir parsing de data no extrato Itaú`
- `refactor: extrair lógica de deduplicação para módulo próprio`

Proibido em mensagens de commit: emojis, nomes de ferramentas de IA, inglês.

---

## Pre-Commit

Antes de commitar, rode o check automatizado:

```bash
./scripts/pre-commit-check.sh
```

Esse script valida: lint (ruff), ausência de emojis, ausência de menções a IA, e formatação geral. O commit será rejeitado se qualquer check falhar.

---

## Issues

- Use GitHub Issues para reportar bugs, sugerir features ou registrar débitos técnicos
- Nunca use `# TODO` ou `# FIXME` inline no código -- crie uma issue
- Descreva o problema ou proposta de forma objetiva, com contexto suficiente para reprodução

---

<!-- "A simplicidade é a sofisticação suprema." -- Leonardo da Vinci -->
