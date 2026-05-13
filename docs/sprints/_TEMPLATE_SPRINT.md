---
id: <SLUG-EM-CAIXA-ALTA>
titulo: <descrição curta em uma linha>
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-13
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint <SLUG-EM-CAIXA-ALTA>

## Contexto

Por que esta sprint existe. Qual sintoma operacional, achado de auditoria ou pedido do dono motivou. Cite arquivos/linhas reais quando aplicável.

## Objetivo

Uma frase declarando o resultado verificável esperado (ex: "ETL ingere XLSX do C6 sem duplicar com OFX nativo").

## Validação ANTES (grep obrigatório — padrão (k))

Comandos de grep/rg que CONFIRMAM (ou refutam) a hipótese da spec. Sempre rodar antes de codar.

```bash
rg "identificador_alvo" src/ --count
ls path/que/deveria/existir
```

## Não-objetivos (escopo fechado — padrão (t))

- O que esta sprint EXPLICITAMENTE não faz.
- Lista de arquivos que NÃO devem ser tocados.

## Touches autorizados

Lista exata de paths que o executor pode modificar/criar:

- `src/.../arquivo.py` — motivo
- `tests/test_arquivo.py` — motivo

## Plano de implementação

Passos granulares (5-10 itens) que o executor segue em ordem.

## Acceptance

Critérios testáveis. Cada item deve ser verificável por comando.

- `comando` retorna `<saída esperada>`.
- `pytest tests/test_x.py` passa N casos.
- `make lint` exit 0.

## Proof-of-work runtime real (padrão (u))

Comando que mostra efeito esperado em dados/runtime reais (não só pytest):

```bash
./run.sh --smoke
python -m src.pipeline.<modulo>
```

## Padrão canônico aplicável

Liste padrões `(a)..(zz)` do BRIEF que se aplicam a esta sprint.

---

*"Citação opcional encerra a spec." — autor*
