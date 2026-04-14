# Sprint 04 - Inteligencia de Categorizacao e Validacao

## Objetivo

Elevar a precisao da categorizacao com overrides manuais e deteccao de padroes novos, implementar tagging automatico para IRPF e criar validador de integridade do pipeline.

## Entregas

- [x] Categorizer aprendiz: leitura de overrides.yaml com prioridade sobre regex
- [x] Categorizer aprendiz: deteccao de padroes nao mapeados (3+ ocorrencias)
- [x] Categorizer aprendiz: suporte a regra_valor nos overrides (ex: Ki-Sabor >=800)
- [x] Tag IRPF automatica: rendimentos tributaveis (G4F, Infobase, salarios)
- [x] Tag IRPF automatica: rendimentos isentos (NEES/UFAL, FGTS, poupanca)
- [x] Tag IRPF automatica: despesas dedutiveis medicas (clinicas, hospitais, dentistas, planos)
- [x] Tag IRPF automatica: impostos pagos (DARF, DAS MEI, Receita Federal)
- [x] Tag IRPF automatica: INSS retido
- [x] Validador de integridade: total de transacoes por banco
- [x] Validador de integridade: alerta de transacoes sem categoria
- [x] Validador de integridade: classificacoes validas
- [x] Validador de integridade: duplicatas residuais
- [x] Validador de integridade: meses com receita zero
- [x] Validador de integridade: despesa > receita
- [x] Integracao no pipeline como passo 7 (apos categorizar, antes de filtrar)

## Arquivos Criados

| Arquivo | Descricao |
|---------|-----------|
| `mappings/overrides.yaml` | 10 overrides manuais (nomes pessoais, Ki-Sabor) |
| `src/transform/irpf_tagger.py` | 21 regras IRPF em 5 tipos de tag |
| `src/utils/validator.py` | 6 validacoes de integridade, executavel via CLI |

## Arquivos Modificados

| Arquivo | Mudanca |
|---------|---------|
| `src/transform/categorizer.py` | Refatorado: overrides como prioridade 1, deteccao de padroes novos |
| `src/pipeline.py` | Integrado irpf_tagger como passo 7 |

## Resultados da Validacao

| Metrica | Valor |
|---------|-------|
| Transacoes processadas | 2859 |
| Categorizacao | 100% (0 sem categoria) |
| Classificacoes validas | Obrigatorio(1152), Questionavel(914), Superfluo(405), N/A(388) |
| Tags IRPF | 79 registros (aumento de 25%) |
| Duplicatas residuais | 16 (coincidencias legitimas) |
| Meses sem receita | 15 (historico sem dados de renda) |
| Meses com deficit | 7 (meses reais de despesa > receita) |

## Detalhes Tecnicos

### Overrides (overrides.yaml)
Correcoes manuais com prioridade sobre regex. Suportam `regra_valor` para decisoes baseadas em valor (ex: Ki-Sabor >= R$ 800 = Aluguel). Verificados por substring case-insensitive antes das regras regex.

### IRPF Tagger (irpf_tagger.py)
21 regras compiladas em 5 tipos de tag:
- `rendimento_tributavel`: G4F, Infobase, salarios genericos
- `rendimento_isento`: NEES/UFAL, FGTS, rendimentos de poupanca
- `dedutivel_medico`: clinicas, hospitais, psicologos, dentistas, laboratorios, planos de saude
- `imposto_pago`: DARF, DAS MEI, Receita Federal
- `inss_retido`: INSS descontado

Nao sobrescreve tags ja existentes (overrides/categorizer tem prioridade).

### Validador (validator.py)
6 checagens executaveis via `python -m src.utils.validator`:
1. Total por banco (consistencia)
2. Transacoes sem categoria (deve ser zero)
3. Classificacoes validas (4 valores aceitos)
4. Duplicatas residuais (mesma data+valor+local)
5. Meses com receita zero (alerta informativo)
6. Despesa > receita (alerta informativo)

Exit code 0 se tudo OK, 1 se qualquer alerta.

## Dependencias

Sprint 3 (dashboard funcional) -- concluida.

## Criterio de Sucesso

- [x] Validador roda sem erros criticos
- [x] 100% das transacoes categorizadas automaticamente
- [x] Tags IRPF aplicadas corretamente nas transacoes elegiveis
- [x] Pipeline integrado e funcional com irpf_tagger

## Concluida em 2026-04-14
