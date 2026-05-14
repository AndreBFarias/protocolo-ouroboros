---
id: FASE-A-GRADUACAO-MASSA-2026-05-13
titulo: Graduar próximos 9 tipos da Fase A para atingir meta ≥15 GRADUADOS do roadmap
status: pendente
data_criacao: 2026-05-13
prioridade: P0
fase: A
epico: 1
depende_de: [META-FIX-DOSSIE-TIPO-BUGS-2026-05-13]
origem: sessão 2026-05-13 fechou 6 tipos (pix, cupom, holerite, das_parcsn, nfce, boleto_servico). Roadmap exige ≥15. Restam 9 tipos canônicos do `mappings/tipos_documento.yaml` sem dossiê ou com dossiê esqueleto.
---

# Sprint FASE-A-GRADUACAO-MASSA-2026-05-13

## Contexto

Estado em 2026-05-13 23:55 BRT:

| Tipo | Status | Amostras OK |
|---|---|---|
| comprovante_pix_foto | GRADUADO | 3 |
| cupom_fiscal_foto | GRADUADO | 3 |
| holerite | GRADUADO | 2 |
| das_parcsn | GRADUADO | 2 |
| nfce_modelo_65 | GRADUADO | 2 |
| boleto_servico | GRADUADO | 2 |
| dirpf_retif | PENDENTE (bloqueado, ver spec separada) | -- |

Faltam **9 tipos** para chegar a 15 GRADUADOS (meta roadmap).

## Tipos alvo (em ordem de prioridade por volume real no grafo)

Para cada tipo, levantar quantas amostras existem em `data/raw` antes de comprometer. Quem tem mais amostras grada primeiro:

| Tipo | Pasta esperada em data/raw | Hipótese |
|---|---|---|
| das_mei | `data/raw/{pessoa}/impostos/das_mei/` | DARFs DAS de MEI ativo (não-PARCSN). |
| irpf_parcela | `data/raw/{pessoa}/impostos/irpf_parcelas/` | DARF parcela IRPF anual. |
| fatura_cartao | `data/raw/{pessoa}/cartoes/` | PDF de fatura mensal. Provavelmente abundante. |
| extrato_bancario | `data/raw/{pessoa}/extratos/` ou `extrato_c6_pdf` separado | OFX ou PDF. |
| conta_luz | `data/raw/{pessoa}/contas/luz/` | CEB/Neoenergia DF. |
| conta_agua | `data/raw/{pessoa}/contas/agua/` | CAESB DF. |
| recibo_nao_fiscal | `data/raw/{pessoa}/recibos/` | recibo manuscrito ou online. |
| comprovante_cpf | `data/raw/{pessoa}/documentos/cpf/` | comprovante RFB. |
| certidao_receita_cnpj | `data/raw/{pessoa}/empresa/` | certidão CNPJ ativa. |

## Hipótese e validação ANTES

H1: para cada tipo, ≥2 amostras reais existem em `data/raw` (não verificado).

```bash
# Levantamento rápido (rodar antes de comprometer)
for tipo in das_mei irpf_parcela fatura_cartao extrato_bancario conta_luz conta_agua recibo_nao_fiscal comprovante_cpf certidao_receita_cnpj; do
  echo "=== $tipo ==="
  find data/raw -type f \( -iname "*$tipo*" -o -iname "*$(echo $tipo | tr _ - )*" \) 2>/dev/null | head -3
done

# Se < 2 amostras: tipo entra em backlog separado "FASE-A-AGUARDA-AMOSTRAS-<tipo>".
```

## Entregável

Para cada tipo X com >= 2 amostras reais:

1. `scripts/dossie_tipo.py abrir X`.
2. Selecionar 2-3 amostras representativas (emissor/competência distintos).
3. Supervisor Opus principal lê cada PDF/imagem via Read multimodal (etapas 3+5 do CICLO, exclusividade do Opus interativo).
4. Gerar cache OCR + prova artesanal subset (mesmo fluxo aplicado em comprovante_pix_foto, cupom, holerite, das_parcsn, nfce, boleto na sessão 2026-05-13).
5. `comparar` retorna GRADUADO_OK para >= 2 amostras.
6. `graduar-se-pronto X` transiciona PENDENTE → GRADUADO.

Para cada tipo Y com < 2 amostras: registrar spec-filha `FASE-A-AGUARDA-AMOSTRAS-<Y>` no backlog, com instrução de coleta para o dono.

## Acceptance

- `data/output/graduacao_tipos.json` mostra ≥ 15 GRADUADOS (meta do roadmap).
- Tipos sem amostra suficiente têm spec-filha aberta (anti-débito padrão (l)).
- `make lint`, `make smoke`, `pytest` mantêm verde.
- Spec movida para `concluidos/` com `concluida_em: YYYY-MM-DD`.

## Não-objetivos

- Não despachar executor para etapas 3-5 (multimodal exclusivo do Opus principal -- padrão (jj)).
- Não inventar amostras sintéticas.
- Não graduar tipo com 1 amostra "para chegar a 15" -- ritual exige >=2.

## Proof-of-work runtime-real

```bash
.venv/bin/python -c "
import json
d = json.load(open('data/output/graduacao_tipos.json'))
graduados = [t for t, info in d['tipos'].items() if info['status'] == 'GRADUADO']
print('GRADUADOS:', len(graduados))
print(sorted(graduados))
assert len(graduados) >= 15, f'apenas {len(graduados)} -- meta nao atingida'
"
```

## Padrões aplicáveis

- (jj) Dossiê obrigatório antes de código.
- (kk) Sprint encerra com produto final (cada tipo grada na hora ou registra spec-filha).
- (ll) Re-trabalho em loop fechado (divergência gera sprint-filha automática).
- (k) Hipótese da spec não é dogma (grep antes de comprometer).
- (x) Monolito sem subdivisão -- se 9 tipos virar trabalho monolítico, dividir em ondas de 3.

## Sequência recomendada (3 ondas de 3 tipos)

```
Onda 1 (financeiro pesado):
  fatura_cartao + extrato_bancario + conta_luz
Onda 2 (impostos):
  das_mei + irpf_parcela + certidao_receita_cnpj
Onda 3 (variado):
  conta_agua + recibo_nao_fiscal + comprovante_cpf
```

Cada onda fecha com `graduar-se-pronto` + lint/smoke + commit `feat(FASE-A): graduar onda N`.

---

*"Roadmap não exige velocidade; exige fechamento. Tipo graduado eh tipo que para de pedir atenção." -- princípio do mapa que se apaga ao caminhar*
