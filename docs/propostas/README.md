# docs/propostas/ -- Workflow Supervisor Artesanal

Este diretório é o inbox de **propostas** feitas pelo supervisor artesanal
(o Claude Code rodando em sessão interativa, conforme ADR-13) para o humano
aprovar ou rejeitar.

Propostas são o mecanismo canônico de absorver:

- Novos padrões detectados no pipeline que merecem virar regra determinística
  (regex em `mappings/categorias.yaml`, seguradora em `mappings/seguradoras.yaml`,
  layout SEFAZ em `mappings/layouts_nfce.yaml`, etc.).
- Arquivos em `data/raw/_classificar/` que não foram reconhecidos pelo
  intake e precisam de decisão humana (novo tipo de documento? regra
  nova? descartar?).
- Linking ambíguo entre documento e transação quando a heurística do
  ingestor não resolve.
- Entity resolution de fornecedores/itens quando rapidfuzz dá
  sugestão fraca.
- Categorização manual de itens de compra (supermercado: o `item` "DEO
  CREME DOVE HIDRATANTE" é "Higiene" ou "Cosmético"?).

Ver também: `docs/ARMADILHAS.md` (aprendizados que geraram propostas),
`docs/DIARIO_MELHORIAS.md` (log cronológico de decisões).

---

## Tipos de proposta

| Tipo | Template | Quando usar |
|------|----------|-------------|
| `regra` | `docs/templates/PROPOSTA_REGRA.md` | Adicionar/alterar regex em `mappings/*.yaml` |
| `classificacao` | `docs/templates/PROPOSTA_CLASSIFICACAO.md` | Arquivo em `data/raw/_classificar/` precisa de tipo + destino |
| `linking` | `docs/templates/PROPOSTA_LINKING.md` | Ligar documento ↔ transação quando heurística é ambígua |
| `resolver` | `docs/templates/PROPOSTA_REGRA.md` | Unificar entidades (fornecedor/item) que `entity_resolution.py` não casou |
| `categoria_item` | `docs/templates/PROPOSTA_REGRA.md` | Classificar item de NFC-e em categoria temática |

## Estrutura de pastas

```
docs/propostas/
├── README.md                        -- este arquivo
├── regra/
│   ├── 2026-04-20_slug.md           -- proposta aberta
│   ├── _aprovadas/                  -- após supervisor_aprovar.sh
│   └── _rejeitadas/                 -- após supervisor_rejeitar.sh
├── classificacao/
│   ├── ... (mesmo padrão)
├── linking/
│   ├── ...
├── sprint_XX_conferencia.md         -- conferências artesanais de sprints
└── sprint_nova/                     -- propostas de sprint novas (antes de virar backlog)
```

## Ciclo de vida

```
           proposta_nova.sh                supervisor_aprovar.sh
  -----------------------------→  aberta  ------------------→  _aprovadas/
                                    │                     ↓
                                    │     registra em DIARIO_MELHORIAS.md
                                    │
                                    │        supervisor_rejeitar.sh "motivo"
                                    └-----------------------→  _rejeitadas/
                                                          ↓
                                                registra motivo + diário
```

Uma proposta aprovada ainda NÃO é regra no código. Ela é o **mandato**:
o humano decidiu que vira regra. O próximo commit (`feat: absorve proposta
<id>`) implementa o diff descrito na proposta em `mappings/*.yaml` ou no
código-fonte apropriado.

## Frontmatter obrigatório

Todo arquivo de proposta começa com:

```yaml
---
id: <yyyy-mm-dd>_<slug>
tipo: regra | classificacao | linking | resolver | categoria_item
data: YYYY-MM-DD
status: aberta
autor_proposta: claude-code-opus | humano | outro
sprint_contexto: NN                # sprint em que a proposta surgiu (número ou "none")
---
```

Campos `aprovada_em`, `rejeitada_em` e `motivo_rejeicao` são preenchidos
pelos scripts de aprovação/rejeição.

## Comandos

Abrir proposta:
```bash
bash scripts/supervisor_proposta_nova.sh regra neoenergia_v2
# cria docs/propostas/regra/2026-04-20_neoenergia_v2.md
```

Aprovar proposta:
```bash
bash scripts/supervisor_aprovar.sh docs/propostas/regra/2026-04-20_neoenergia_v2.md
# move para _aprovadas/, registra em DIARIO_MELHORIAS.md, imprime guidance
```

Rejeitar proposta:
```bash
bash scripts/supervisor_rejeitar.sh docs/propostas/regra/2026-04-20_neoenergia_v2.md \
    "regex muito frouxa -- casaria Neo Química"
# move para _rejeitadas/, registra motivo em DIARIO_MELHORIAS.md
```

Ver estado do projeto (contexto inicial de sessão):
```bash
./run.sh --supervisor
```

## Convenções

- **Nome do arquivo:** `YYYY-MM-DD_slug.md` -- ordenação cronológica natural.
- **Slug:** kebab-case sem acentos (ex.: `neoenergia-v2`, não `neoenergia_v2`
  nem `NeoenergiaV2`).
- **Justificativa:** toda proposta precisa de `## Justificativa` com contagem
  ("essa regra acerta N transações que hoje caem em Outros/Questionável").
- **Teste de regressão:** toda proposta precisa de comando reproduzível
  (pytest, script de inspeção) que prova que a mudança faz o que diz.
- **Decisão humana:** só o humano aprova/rejeita. O Claude Code propõe e
  argumenta, mas não pressiona a execução dos scripts.

## Anti-padrões

- Proposta sem `## Justificativa` concreta (não aceita).
- Proposta que altera código-fonte diretamente em vez de `mappings/*.yaml`
  (Isso é refactor disfarçado de proposta -- vira sprint.)
- Rodar `supervisor_aprovar.sh` sem o humano ter lido o diff. Aprovação
  cega viola ADR-13.
- Proposta resolvendo ao mesmo tempo 2 problemas ortogonais (dividir em
  2 propostas distintas -- scope atômico do CLAUDE.md §9.5).

---

*"O mestre não se serve sem ritual, nem o aprendiz sem calma." -- princípio de artesão*
