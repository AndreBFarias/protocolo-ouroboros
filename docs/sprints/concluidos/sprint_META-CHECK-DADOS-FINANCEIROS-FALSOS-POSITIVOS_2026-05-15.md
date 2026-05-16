---
id: META-CHECK-DADOS-FINANCEIROS-FALSOS-POSITIVOS
titulo: Revisar 2 falsos-positivos de `check_dados_financeiros` em `src/utils/logger.py`
status: concluida
concluida_em: 2026-05-15
prioridade: P3
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 0.5
origem: achado colateral da sprint META-HOOKS-AUDITAR-E-WIRAR (executor `af13dd9f`, 2026-05-15). Hook `check_dados_financeiros` flagou 2 ocorrências em `src/utils/logger.py:21` e `:23` como dados financeiros, mas são padrões de log canônico (não valores reais). Falsos-positivos bloqueiam commits legítimos.
---

# Sprint META-CHECK-DADOS-FINANCEIROS-FALSOS-POSITIVOS

## Contexto

`hooks/check_dados_financeiros.py` é o único hook que estava ativo antes da auditoria. Detecta vazamento de PII financeira (CPF, CNPJ, valores reais) em commits. Mas em `src/utils/logger.py:21,23` ele flagra strings que parecem padrões mas são apenas formato de log (ex: `"%.2f"` em template ou similar).

3 caminhos: (a) ajustar regex do hook para excluir padrões de format string; (b) adicionar `# noqa: dados-financeiros` em `src/utils/logger.py`; (c) excluir `src/utils/logger.py` do `exclude:` pattern do hook em `.pre-commit-config.yaml`.

## Hipótese e validação ANTES

```bash
python hooks/check_dados_financeiros.py src/utils/logger.py 2>&1 | head -10
# Esperado: 2 hits em linhas 21 e 23

sed -n '18,25p' src/utils/logger.py
# Ler contexto exato das linhas marcadas
```

## Objetivo

1. Ler `src/utils/logger.py:21,23` e classificar se é falso-positivo.
2. Aplicar opção mais segura (provavelmente (b) — `# noqa` inline com motivo).
3. Validar pre-commit run no arquivo limpo.

## Não-objetivos

- Não enfraquecer o hook (não remover regras genuinamente úteis).
- Não tocar outros arquivos.

## Proof-of-work runtime-real

```bash
python hooks/check_dados_financeiros.py src/utils/logger.py
# Esperado: exit 0

.venv/bin/pre-commit run check-dados-financeiros --files src/utils/logger.py
# Esperado: passed
```

## Acceptance

- 0 falsos-positivos em `src/utils/logger.py`.
- Pre-commit run exit 0.
- Pytest > 3046. Lint exit 0.

## Padrões aplicáveis

- (e) PII never in INFO log — hook continua valendo, só refinamos a fronteira.
- (a) Edit cirúrgico.

---

*"Falso-positivo treina o usuário a ignorar o sensor." — princípio do alerta credível*
