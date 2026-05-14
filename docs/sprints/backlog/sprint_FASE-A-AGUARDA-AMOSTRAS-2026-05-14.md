---
id: FASE-A-AGUARDA-AMOSTRAS-2026-05-14
titulo: Aguarda coleta humana de amostras para 13 tipos canonicos da Fase A
status: aguardando-amostras
data_criacao: 2026-05-14
prioridade: P0
fase: A
epico: 1
depende_de: [coleta humana do dono]
parent: FASE-A-GRADUACAO-MASSA-2026-05-13
origem: sessao 2026-05-14 (supervisor autonomo) graduou 3 novos tipos (fatura_cartao, extrato_bancario, cupom_garantia_estendida). Auditoria provou que outros 13 tipos canonicos do `mappings/tipos_documento.yaml` nao tem amostras suficientes em `data/raw` para o ritual canonico (>=2 amostras distintas em SHA-256).  <!-- noqa: accent -->

---

# Sprint FASE-A-AGUARDA-AMOSTRAS-2026-05-14

## Contexto

Estado em 2026-05-14 01:50 BRT:

- **9 tipos GRADUADOS** no `graduacao_tipos.json`: boleto_servico, comprovante_pix_foto, cupom_fiscal_foto, cupom_garantia_estendida, das_parcsn, extrato_bancario, fatura_cartao, holerite, nfce_modelo_65.
- **1 PENDENTE bloqueado**: dirpf_retif (ritual inviavel -- spec separada).  <!-- noqa: accent -->
- **Meta do roadmap**: >=15 tipos GRADUADOS.
- **Gap**: 6 tipos.

A escassez nao e tecnica -- e fisica. O dono precisa coletar amostras reais via `inbox/` e classificar nas pastas canonicas. Esta spec funciona como checklist de coleta.  <!-- noqa: accent -->

## Hipotese e validacao ANTES  <!-- noqa: accent -->

H1: tipos listados abaixo nao tem amostras suficientes em `data/raw`. CONFIRMADO via levantamento exaustivo na sessao 2026-05-14 (logs em historico de comandos).  <!-- noqa: accent -->

```bash
# Re-confirmar antes de iniciar coleta (regra (k) -- nao confiar em snapshot velho):
for tipo in das_mei irpf_parcela conta_luz conta_agua recibo_nao_fiscal comprovante_cpf certidao_receita_cnpj receita_medica garantia_fabricante contrato danfe_nfe55 xml_nfe extrato_c6_pdf; do
  echo "=== $tipo ==="
  find data/raw -type f \( -iname "*$tipo*" -o -iname "*$(echo $tipo | tr _ -)*" \) 2>/dev/null | head -3
done
```

## Tipos aguardando coleta

Ordenado por probabilidade de o dono ter o documento em maos / Drive / email:  <!-- noqa: accent -->

### Grupo A: alta probabilidade (impostos e identidade)

| Tipo | O que coletar | Onde costuma estar | Quantidade alvo |
|---|---|---|---|
| das_mei | DARF DAS de MEI ativo (Vitoria?) | Portal MEI / RFB / Simples Nacional | >=2 competencias distintas |
| irpf_parcela | DARF parcela IRPF anual | Portal e-CAC RFB | >=2 parcelas distintas |
| comprovante_cpf | Comprovante de situacao cadastral CPF (RFB) | https://servicos.receita.fazenda.gov.br | >=2 (Andre + Vitoria + Carol) |  <!-- noqa: accent -->

| certidao_receita_cnpj | Certidao negativa CNPJ ativa | https://servicos.receita.fazenda.gov.br | >=2 CNPJs distintos (Andre tem 1; Vitoria tem MEI?) |

### Grupo B: contas de servico recorrente (mensal facil)

| Tipo | O que coletar | Emissor DF | Quantidade alvo |
|---|---|---|---|
| conta_luz | Conta de energia residencial | Neoenergia DF / CEB | >=2 meses distintos |
| conta_agua | Conta de agua/esgoto residencial | CAESB | >=2 meses distintos |

### Grupo C: documentos avulsos

| Tipo | O que coletar | Fonte | Quantidade alvo |
|---|---|---|---|
| recibo_nao_fiscal | Recibo manuscrito ou online (servicos, autonomos) | Diversos | >=2 emissores distintos |
| receita_medica | Receita medica controlada ou comum | Medicos/clinicas | >=2 prescritores distintos |
| garantia_fabricante | NF/manual com termo de garantia do fabricante | Caixas de produtos comprados | >=2 produtos distintos |
| contrato | Contrato de locacao, prestacao, financiamento | Cartorios/imobiliarias | >=2 contratos distintos |
| danfe_nfe55 | DANFE PDF (NFe modelo 55, formal A4 com destinatario) | Compras corporativas | >=2 NFs distintas |
| xml_nfe | XML de NFe (modelo 55 ou 65) | Anexo de email pos-compra | >=2 XMLs distintos |
| extrato_c6_pdf | Extratos C6 PDF de competencias distintas | App C6 -> exportar PDF | >=1 a mais (1 ja existe) |

## Entregavel por tipo coletado

Para cada amostra adicionada via `inbox/`:

1. Dono executa `./run.sh --full-cycle` (ingestao + classificacao + pipeline).  <!-- noqa: accent -->

2. Supervisor (Opus interativo) abre dossie do tipo: `scripts/dossie_tipo.py abrir <tipo>`.
3. Supervisor le amostra via Read multimodal, gera cache OCR artesanal em `data/output/opus_ocr_cache/<sha>.json` (extraido_via: opus_supervisor_artesanal, eh_gabarito_real: true).
4. Supervisor cria prova artesanal subset em `data/output/dossies/<tipo>/provas_artesanais/<sha>.json`.
5. `dossie_tipo.py comparar <tipo> <sha>` -> deve retornar GRADUADO_OK.
6. Apos >=2 amostras OK, `dossie_tipo.py graduar-se-pronto <tipo>` transiciona para GRADUADO.

## Acceptance

- `data/output/graduacao_tipos.json` mostra GRADUADO para cada tipo que recebeu >=2 amostras processadas.
- Meta do roadmap (>=15 GRADUADOS) atinge-se ao graduar 6 destes 13 tipos (ordem nao importa).  <!-- noqa: accent -->
- Cada tipo coletado vira commit `feat(FASE-A): graduar <tipo>` em onda separada para rastreabilidade.

## Nao-objetivos  <!-- noqa: accent -->

- Nao inventar amostras sinteticas (padrao (gg) -- cache sintetico e placeholder honesto, nao graduador).  <!-- noqa: accent -->
- Nao tentar OCR via PyTesseract para suprir falta de amostras (multimodal artesanal e exclusividade do supervisor Opus).  <!-- noqa: accent -->
- Nao fazer auto-coleta via API de banco/RFB neste momento (Epico 4 endereca scraping legal).  <!-- noqa: accent -->

## Proof-of-work runtime-real

```bash
# Apos coletar amostras e graduar:
.venv/bin/python -c "
import json
d = json.load(open('data/output/graduacao_tipos.json'))
graduados = [t for t, info in d['tipos'].items() if info['status'] == 'GRADUADO']
print(f'GRADUADOS: {len(graduados)}')
print(sorted(graduados))
"
```

## Padroes aplicaveis

- (jj) Dossie obrigatorio antes de codigo.  <!-- noqa: accent -->
- (kk) Sprint encerra com produto final (cada tipo grada na hora ou registra spec-filha).
- (ll) Re-trabalho em loop fechado.
- (k) Hipotese da spec nao e dogma (grep antes de comprometer).  <!-- noqa: accent -->

## Instrucao operacional para o dono (Andre)  <!-- noqa: accent -->

Quando voce tiver tempo, jogue arquivos das pastas abaixo no `inbox/` (de qualquer pessoa) e rode `./run.sh --full-cycle`:  <!-- noqa: accent -->

- **Impostos** (Grupo A): DARFs DAS MEI da Vitoria, DARFs parcela IRPF, comprovante CPF de Carol e Vitoria, certidao CNPJ ativa.
- **Contas** (Grupo B): boleto/PDF da Neoenergia + CAESB de 2-3 meses recentes.
- **Diversos** (Grupo C): NFs em PDF com termo de garantia, contratos guardados, XMLs de NFe (geralmente vem por email da loja apos compra).

Ordem sugerida: Grupo A primeiro (mais rapido, alta certeza de existencia). Grupo B segundo (mensal, facil baixar). Grupo C terceiro (esforco humano maior).

---

*"Tipo nao graduado nao e falha de codigo; e falha de amostra. Coletar e quase tudo; ETL e quase nada." -- principio do gargalo humano*  <!-- noqa: accent -->
