---
id: FASE-A-COMPLETAR-VALIDACAO-ARTESANAL  <!-- noqa: accent -->
titulo: Fechar o ciclo de validação artesanal Opus multimodal para todos os tipos documentais aceitos
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-13
fase: PRODUCAO_READY
depende_de: []
esforco_estimado_horas: 16
origem: lembrete do dono em 2026-05-13 sobre a ideia central do projeto. ETL só pode rodar autônomo (./run.sh --tudo sem revisão humana) quando cada tipo documental teve ≥2 amostras validadas artesanalmente: supervisor Opus lê multimodal a foto/PDF, gera "prova dos nove" canônica, ETL é executado, resultados batem 4-way (Opus × ETL × Grafo × Humano). Sem 2 amostras graduadas, o tipo fica em "calibrando".
---

# Sprint FASE-A-COMPLETAR-VALIDACAO-ARTESANAL  <!-- noqa: accent -->

## Ideia central reforçada

O projeto é um **pipeline auto-validado**. Cada tipo documental tem 3 estados (mesma semântica do `skill_d7_log.json`):

- **PENDENTE**: nenhuma amostra validada artesanalmente.
- **CALIBRANDO**: 1 amostra validada; precisa de mais 1 para graduar.
- **GRADUADO**: ≥2 amostras 4-way verdes; ETL processa esse tipo sem revisão.
- **REGREDINDO**: graduado já, mas amostra recente divergiu (alerta).

Estado dos tipos hoje (audit 2026-05-13):

| Tipo | Status | Evidência |
|---|---|---|
| `cupom_fiscal_foto` | GRADUADO | 5 caches reais (NSP, Atacadão), Fase A 2026-05-12 |
| `holerite` | GRADUADO | 24 holerites no grafo, G4F+INFOBASE validados |
| `das_parcsn` | GRADUADO | 19 DAS no grafo, parcela 4/25 + 17/25 validadas |
| `nfce_modelo_65` | GRADUADO | 2 NFCes (Lojas), PS5+supermercado |
| `comprovante_pix_foto` | CALIBRANDO | 3 caches reais (Itaú/C6/Nubank), mas 4-way não rodou ainda |
| `boleto_servico` | PENDENTE | 2 boletos no grafo, sem validação artesanal |
| `dirpf_retif` | PENDENTE | 1 DIRPF, sem validação artesanal |
| `recibo_nao_fiscal` | PENDENTE | sem amostras |
| `receita_medica` | PENDENTE | sem extrator |
| `conta_agua` | PENDENTE | sem extrator |
| `fatura_cartao` | PENDENTE | sem extrator (extratores bancários cobrem indiretamente) |
| `garantia_fabricante` | PENDENTE | sem extrator (cupom_garantia_estendida ≠) |
| `extrato_bancario` | GRADUADO de fato | bancos C6/Nubank/Itaú/Santander tem extratores |
| `comprovante_cpf` | PENDENTE | tipo declarado, sem amostra |
| `certidao_receita_cnpj` | PENDENTE | idem |

## Objetivo

1. **Para tipos CALIBRANDO**: rodar `./run.sh --tudo`, comparar saída do ETL contra cache Opus (gerado artesanalmente). Se bate → graduar. Sub-sprint dedicada por tipo.
2. **Para tipos PENDENTE com extrator**: coletar 2 amostras reais (dono fornece via inbox), aplicar ritual.
3. **Para tipos PENDENTE sem extrator**: criar sprint-filha "INFRA-EXTRATOR-<TIPO>" que entrega extrator + ritual. Bloqueia até dono fornecer 2+ amostras.
4. **Snapshot único de graduação**: `data/output/graduacao_tipos.json` atualizado a cada validação. Dashboard mostra a tabela acima auto-atualizada.

## Decomposição em sub-sprints (cada uma 2-4h)

- `FASE-A-VALIDAR-PIX` (P0, 2h) -- 3 caches PIX já existem; falta o ritual 4-way + grad.
- `FASE-A-VALIDAR-BOLETO-SERVICO` (P1, 3h) -- coletar 2 amostras + ritual.
- `FASE-A-VALIDAR-DIRPF` (P1, 4h) -- DIRPF é caso especial (total=0.0 já filtrado), mas vale graduar.
- `INFRA-EXTRATOR-RECEITA-MEDICA` (P1, 6h) -- extrator + ritual.
- `INFRA-EXTRATOR-CONTA-AGUA` (P2, 4h) -- idem.
- `INFRA-EXTRATOR-GARANTIA-FABRICANTE` (P2, 4h) -- idem.
- `INFRA-EXTRATOR-FATURA-CARTAO-PDF` (P2, 6h) -- fatura PDF nativa.
- `INFRA-EXTRATOR-RECIBO-NAO-FISCAL` (P3, 4h) -- já tem entrada YAML mas sem extrator.
- `UX-DASH-GRADUACAO-TIPOS` (P2, 3h) -- página mostra a tabela viva.

## Proof-of-work

```bash
.venv/bin/python -c "
import json
g = json.load(open('data/output/graduacao_tipos.json'))
graduados = [k for k,v in g.items() if v['status']=='GRADUADO']
print(f'GRADUADOS: {len(graduados)}')
print(graduados)
"
# Meta: 10+ tipos GRADUADOS antes de declarar 'prod ready'
```

## Acceptance

- `data/output/graduacao_tipos.json` populado.
- ≥10 tipos em status GRADUADO.
- Página `src/dashboard/paginas/graduacao_tipos.py` exibe tabela viva.
- 9 sub-sprints listadas acima registradas em backlog/.
- ETL `./run.sh --tudo` roda autônomo para os tipos graduados.

---

*"Validar artesanalmente uma vez é trabalho; validar 2 vezes é confiança; ETL faz o resto." -- princípio da Fase A*
