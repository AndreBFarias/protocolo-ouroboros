# ADR-23 — Identidade genérica `pessoa_a` / `pessoa_b` no backend Python

- **Status:** aceita
- **Data:** 2026-05-01
- **Sprint:** MOB-bridge-1
- **Sucessor de:** —
- **Cruzamento:** ADR-0011 do repositório companion mobile
  (`Protocolo-Mob-Ouroboros/docs/ADRs/ADR-0011-pessoa-a-b.md`)

## Contexto

Antes desta sprint, todo o código Python referenciava o casal por nome
real (`"André"`, `"Vitória"`) em:

- coluna `quem` do XLSX consolidado (8 abas);
- `inferir_pessoa()` no normalizer;
- 5 extratores bancários (`c6_cartao`, `c6_cc`, `santander_pdf`,
  `itau_pdf`, `nubank_*`) gravando `pessoa="André"` direto na
  `Transacao`;
- detector de pessoa em `intake/`;
- agregação no relatório markdown e filtros do dashboard Streamlit.

51 ocorrências em 22 arquivos `src/` mais 154 asserts em `tests/`
viam o nome real circular livremente em código versionado. Em
preparação para tornar o repositório público (e em alinhamento com
o repositório companion mobile, que já adotou identidade genérica
em ADR-0011), é necessário extrair toda referência literal de
identidade do código.

## Decisão

**O backend Python passa a usar identificadores genéricos canônicos
em todo o código e em toda persistência:**

```
pessoa_a    titular primário do casal
pessoa_b    titular secundário
casal       compartilhado / fallback
```

A migração cobre quatro camadas:

1. **Schema do XLSX (coluna `quem`).** Os valores aceitos no schema
   são `pessoa_a` / `pessoa_b` / `casal`. XLSX gerados antes desta
   sprint são migrados in-place via `scripts/migrar_quem_generico.py`
   (idempotente, com backup automático em
   `data/output/_backup_pre_migracao_quem/`).

2. **Resolver canônico (`src/utils/pessoas.py`).** Módulo único que
   exporta:
   - `carregar_pessoas() -> dict` — lê `mappings/pessoas.yaml` e
     cacheia.
   - `resolver_pessoa(cpf, cnpj, razao_social, alias, fallback) -> str`
     — retorna identificador genérico na ordem CPF > CNPJ raiz >
     razão social > alias > fallback.
   - `nome_de(pessoa_id) -> str` — resolve `display_name` para uso
     em UI/relatório local-first (ADR-24).
   - `pessoa_id_de_pasta(path) -> str | None` — camada 2 do detector.
   - `pessoa_id_de_legacy(valor) -> str` — normaliza qualquer rótulo
     histórico para identificador genérico (cobre XLSX antigos com
     rótulo acentuado em runtime sem precisar de migração destrutiva).

3. **Detector + extratores + normalizer.** Deixam de emitir nome
   literal. `Transacao.pessoa`, `inferir_pessoa()` e
   `_detectar_pessoa()` retornam sempre `pessoa_a` / `pessoa_b` /
   `casal`.

4. **Apresentação (relatório, dashboard).** Filtros e agregações
   internas operam sobre o identificador genérico. O `display_name`
   real (André / Vitória) é resolvido em runtime via `nome_de()`
   apenas no momento da exibição. Decisão complementar formalizada
   em ADR-24.

### Compatibilidade com a estrutura física legada

`data/raw/<bucket>/` permanece com aliases `andre` / `vitoria` /
`casal` para preservar 100% dos dados já gravados sem migração
destrutiva. O helper `pasta_fisica_de(pessoa_id)` faz a tradução
em runtime quando router/registry/extratores precisam construir
paths em disco. O detector aceita ambos os formatos como entrada
e devolve o identificador genérico equivalente.

### Anonimato (Regra −1)

`scripts/check_anonimato.sh` espelha o script do mobile e trava
qualquer regressão em `src/`, `tests/` ou `scripts/`. Aceita marker
`# anonimato-allow: <razão>` para exemplos legítimos em docstrings
e fixtures de matcher. As únicas exceções permitidas são:

- `mappings/pessoas.yaml` (gitignored, contém `display_name`);
- `mappings/cpfs_pessoas.yaml.example` (template com placeholders);
- o próprio `scripts/check_anonimato.sh` (declara os padrões);
- documentos históricos em `docs/auditorias/` e
  `docs/HISTORICO_SESSOES.md` (registros).

## Consequências

### Positivas

- Repositório pode ir público sem expor PII em código.
- Coerência cruzada com o companion mobile (ADR-0011).
- O resolver canônico elimina duplicação de lógica de identidade
  espalhada em 22 arquivos, reduzindo superfície de inconsistência.
- Migração in-place dos XLSX com backup automático preserva
  histórico operacional.

### Negativas

- Uma camada a mais de indireção (`pessoa_id_de_legacy`) durante a
  janela em que XLSX antigos podem coexistir com o schema novo.
  O custo é amortizado pelo cache do yaml.
- A estrutura física `data/raw/andre/`/`data/raw/vitoria/` continua
  com nome legacy. Migração da árvore de diretórios é trabalho
  operacional para sprint futura, fora do escopo MOB-bridge-1.

### Neutras

- Testes ganharam marker `# anonimato-allow:` em fixtures que
  precisam de nomes reais para validar matchers do canonicalizer
  (descrições simuladas de PIX). Convenção aceita pelo
  `check_anonimato.sh`.

## Cruzamento

`Protocolo-Mob-Ouroboros/docs/ADRs/ADR-0011-pessoa-a-b.md` define a
mesma decisão para o app companion. Os contratos de cache readonly
gerados pelo backend (futuro escopo MOB-bridge-2) consumirão a
identidade genérica diretamente, sem necessidade de tradução.

## Verificação runtime

```bash
./scripts/check_anonimato.sh                    # Regra -1 (anonimato)
make lint && make smoke && make test            # baseline + invariantes
.venv/bin/python -c "from src.utils.pessoas import resolver_pessoa, nome_de; \
  print(resolver_pessoa(cpf='051.273.731-22'))  # pessoa_a
  print(nome_de('pessoa_a'))                    # André"
```
