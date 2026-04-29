# Auditoria de cobertura — 2026-04-29

> Gerado pelo Opus principal (Claude Code interativo) via skill `/auditar-cobertura` em sessão de 2026-04-29.
> Fonte: `data/output/grafo.sqlite`. Regras carregadas: 111.

## Sumário executivo

- Transações no grafo: **6,086**
- Categorizadas (não-OUTROS): **5,011 (82.3%)**
- Em OUTROS (cabem regra nova): **1,075 (17.7%)**
- Documentos no grafo: 47 (22 órfãos sem aresta `documento_de`)

## Distribuição de categorias

| Categoria | Transações |
|-----------|-----------:|
| OUTROS | 1,075 |
| MERCADO | 606 |
| PAGAMENTO DE FATURA | 443 |
| TRANSFERÊNCIA | 433 |
| FARMÁCIA | 406 |
| DELIVERY | 386 |
| PADARIA | 336 |
| TRANSPORTE | 223 |
| PESSOAL | 189 |
| ENERGIA | 179 |
| COMPRAS ONLINE | 174 |
| BEBIDAS | 106 |
| JUROS/ENCARGOS | 103 |
| PETS | 101 |
| INSUMOS | 99 |
| NATAÇÃO | 92 |
| COMPRAS | 91 |
| IMPOSTOS | 89 |
| CELULAR | 78 |
| SAÚDE | 70 |

## Top 15 fornecedores em OUTROS (candidatos a regra nova)

| Fornecedor | Tx em OUTROS |
|------------|-------------:|
| TRANSF ENVIADA PIX | 189 |
| FATURA DE CARTÃO | 96 |
| PAGAMENTO DA FATURA CARTÃO NUBANK | 38 |
| ALIPAY ALIEXPRESS PIX | 33 |
| TRANSAÇÃO OFX SEM DESCRIÇÃO | 19 |
| RAPHAEL DIAS DA COSTA LACERDA DE FARIAS ••• 548 551 •• BANCO DIGIO 0335 AGÊNCIA 1 CONTA 327713 | 16 |
| EBANX TECNOLOGIA DA INFORMACAO LTDA | 15 |
| SABORELLA SAM | 12 |
| ACELERADOR ÁTOMOS | 12 |
| WILLIAM MARQUES DE SOUZA LIMA ••• 268 301 •• ITAÚ UNIBANCO S A 0341 AGÊNCIA 5079 CONTA 94860 | 11 |
| PLANOS ÁTOMOS | 11 |
| DAVID ÍTALO | 11 |
| BOLETO | 11 |
| PLANOS ATOMOS | 10 |
| JOSE VITOR TELES LIMA ••• 005 821 •• BCO C6 S A 0336 AGÊNCIA 1 CONTA 21183977 | 10 |

## Cobertura por pessoa

| Pessoa | Total | Em OUTROS | % categorizado |
|--------|------:|----------:|---------------:|
| André | 1,940 | 453 | 76.6% |
| Casal | 2,405 | 622 | 74.1% |
| Vitória | 1,741 | 0 | 100.0% |

## Próximos passos sugeridos pelo supervisor

1. Revisar top fornecedores em OUTROS — os 5 primeiros tipicamente concentram >30% do gap.
2. Para cada fornecedor recorrente, decidir: criar regra em `mappings/categorias.yaml` OU usar `/propor-extrator` se faltar extrator dedicado.
3. Documentos órfãos (sem aresta `documento_de`): rodar `LINK-AUDIT-01` (Onda 4) ou ajustar tolerância temporal em `mappings/linking_config.yaml`.
4. Se cobertura por pessoa diverge muito entre André/Vitória, suspeitar de regra que só pega nome de uma das contas.

---

*"O que se mede sem padrão é palpite com etiqueta." — princípio do auditor manual*
