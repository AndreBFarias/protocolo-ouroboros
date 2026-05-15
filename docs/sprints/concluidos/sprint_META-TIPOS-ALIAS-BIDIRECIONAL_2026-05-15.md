---
id: META-TIPOS-ALIAS-BIDIRECIONAL
titulo: Consolidar cisma entre `tipos_documento.yaml` (classifier) e dossiês/grafo via alias
status: concluída
concluida_em: 2026-05-15
prioridade: P0
data_criacao: 2026-05-15
fase: PRODUCAO_READY
epico: 1
depende_de: []
esforco_estimado_horas: 4
origem: auditoria 2026-05-15. `mappings/tipos_documento.yaml` declara 22 IDs canônicos (`nfce_consumidor_eletronica`, `extrato_c6_pdf`...). Mas `data/output/dossies/` + `graduacao_tipos.json` usam 10 nomes diferentes (`nfce_modelo_65`, `extrato_bancario`, `dirpf_retif`). 2 dossiês órfãos do YAML + 14 IDs do YAML sem dossiê. CLAUDE.md declara YAML como "fonte canônica de execução" mas sistema de graduação ignora. Meta ≥15 GRADUADOS fica impossível porque 14 dos 22 não sabem se medir.
---

# Sprint META-TIPOS-ALIAS-BIDIRECIONAL

## Contexto

Dois "registros de verdade" para tipos documentais coexistem e divergiram silenciosamente:

| Registro | Fonte | Conteúdo |
|---|---|---|
| Classifier intake | `mappings/tipos_documento.yaml` | 22 IDs como `nfce_consumidor_eletronica`, `extrato_c6_pdf` |
| Sistema graduação | `data/output/dossies/` + `graduacao_tipos.json` | 10 nomes como `nfce_modelo_65`, `extrato_bancario`, `dirpf_retif` |

Origem provável: nomes do grafo refletem o **conteúdo extraído** (modelo fiscal 65, nome genérico extrato_bancario); nomes do YAML refletem o **roteamento por regex no intake**. Ambos válidos mas não-sincronizados.

Decisão do dono (2026-05-15): manter YAML como canônico e adicionar alias.

## Hipótese e validação ANTES (padrão (k))

H1: 2 dossiês órfãos + 14 IDs sem dossiê. Confirmado:

```bash
for tipo in $(ls data/output/dossies/); do
  existe=$(grep -c "id: $tipo$" mappings/tipos_documento.yaml)
  [ "$existe" = "0" ] && echo "ORFAO: $tipo"
done
# Esperado: ORFAO: dirpf_retif, ORFAO: nfce_modelo_65

for tipo in $(grep "^  - id:" mappings/tipos_documento.yaml | awk '{print $3}'); do
  [ ! -d "data/output/dossies/$tipo" ] && echo "  faltando: $tipo"
done
# Esperado: 14 faltantes
```

H2: `dirpf_retif` é gerado pelo extrator `dirpf_dec.py` (commit `c41f987`) mas não está no `tipos_documento.yaml` (não tem regra de intake). Confirmar com grep.

## Objetivo

1. Adicionar campo `aliases_graduacao` (lista) em cada entry do `mappings/tipos_documento.yaml`. Exemplo:
   ```yaml
   - id: nfce_consumidor_eletronica
     aliases_graduacao: ["nfce_modelo_65"]
     ...
   ```
2. Para `dirpf_retif` (extrator existe sem entry no YAML), adicionar entry mínima no YAML com prioridade `especifico` mesmo que extrator viva separado (`dirpf_dec.py`).
3. Atualizar `scripts/dossie_tipo.py::cmd_listar_tipos` para mostrar alias entre parênteses:
   ```
   nfce_consumidor_eletronica (alias: nfce_modelo_65) [+]
   ```
4. Atualizar `dossie_tipo.py` para aceitar ID canônico OU alias em todos subcomandos (`abrir`, `listar-candidatos`, etc).
5. Atualizar `_carregar_etl_output` para mapear alias → ID canônico ao consultar grafo.
6. NÃO renomear diretórios de dossiês existentes (preservar histórico). Resolução por alias.
7. Atualizar `data/output/graduacao_tipos.json` para chave canônica do YAML (ex: `nfce_consumidor_eletronica`), com campo `aliases` interno.

## Não-objetivos

- Não renomear pastas físicas em `data/output/dossies/` (resolver via mapping).
- Não tocar regras de roteamento `regex_conteudo` do YAML (estáveis).
- Não criar novo arquivo `mappings/tipos_graduacao.yaml` separado (decisão do dono: alias bidirecional no YAML existente).

## Proof-of-work runtime-real

```bash
# 1. Listar tipos mostra aliases
.venv/bin/python scripts/dossie_tipo.py listar-tipos | grep "alias:"
# Esperado: 3+ linhas com alias

# 2. Abrir via alias funciona
.venv/bin/python scripts/dossie_tipo.py abrir nfce_modelo_65 > /tmp/a
.venv/bin/python scripts/dossie_tipo.py abrir nfce_consumidor_eletronica > /tmp/b
diff /tmp/a /tmp/b
# Esperado: zero diff

# 3. Snapshot tem chave canônica
.venv/bin/python scripts/dossie_tipo.py snapshot
python -c "
import json
d = json.load(open('data/output/graduacao_tipos.json'))
assert 'nfce_consumidor_eletronica' in d['tipos']
assert 'nfce_modelo_65' not in d['tipos']  # vira alias
print('OK chave canonica')
"
```

## Acceptance

- 22 entries do YAML com campo `aliases_graduacao` (lista vazia ou populada).
- 3 aliases confirmados: nfce_modelo_65, extrato_bancario, dirpf_retif (este último ganha entry própria).
- 10 dossiês existentes acessíveis via ID canônico OU alias.
- `graduacao_tipos.json` usa chaves canônicas; campo `aliases` interno preserva legacy.
- Roadmap métrica "≥15 GRADUADOS" se torna mensurável (22 tipos com slot próprio).
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (o) Subregra retrocompatível — alias preserva legacy.
- (k) Hipótese validada via grep antes.
- (n) Defesa em camadas — alias resolve em 2 sítios (CLI + JSON snapshot).
- (jj) Dossiê obrigatório — preserva dossiês existentes intactos.

---

*"Dois nomes para uma coisa é confusão; um nome com aliases é tradução." — princípio do dicionário operacional*
