---
id: FASE-A-dirpf_retif-RITUAL-INVIAVEL-2026-05-13
titulo: Graduação de dirpf_retif exige nova rota -- arquivo .DEC binário, fora do ritual multimodal atual
status: bloqueada
data_criacao: 2026-05-13
prioridade: P1
fase: A
epico: 1
depende_de: []
origem: Sprint FASE-A-RESTAURAR-3-TIPOS-2026-05-13 tentou estender restauração para dirpf_retif (único tipo PENDENTE remanescente após graduar holerite/das/nfce/boleto). Bloqueado por 3 razões estruturais que exigem decisão do supervisor, não execução cega.
---

# Sprint FASE-A-dirpf_retif-RITUAL-INVIAVEL-2026-05-13

## Contexto

`dirpf_retif` aparece em `data/output/graduacao_tipos.json` como tipo PENDENTE, mas o ritual canônico de graduação em `docs/CICLO_GRADUACAO_OPERACIONAL.md` não consegue cobri-lo. Esta spec documenta o bloqueio e propõe alternativas.

## Bloqueios identificados na sessão 2026-05-13

### Bloqueio 1: formato .DEC não-multimodal

Única amostra é `data/raw/andre/documentos/dirpf/05127373122-IRPF-A-2026-2025-RETIF.DEC` -- arquivo binário do Programa IRPF da Receita Federal, formato proprietário. `Read` multimodal do Claude Code não suporta esse formato (espera PDF/imagem). O ritual canônico (Fase 3 do CICLO_GRADUACAO) exige leitura multimodal do supervisor, então toda a sequência fica inviável.

### Bloqueio 2: apenas 1 amostra disponível

`scripts/dossie_tipo.py graduar-se-pronto` exige >= 2 amostras OK consecutivas para transicionar PENDENTE → GRADUADO. Apenas 1 .DEC está em `data/raw/andre/documentos/dirpf/`.

### Bloqueio 3: tipo ausente em `mappings/tipos_documento.yaml`

`grep -nE "id: dirpf_retif" mappings/tipos_documento.yaml` retorna zero. O id existente é `irpf_parcela` (DARF de parcela, semanticamente diferente). Apesar disso, o grafo SQLite tem nó id 7768 com `tipo_documento: dirpf_retif` -- significa que algum extrator gera o tipo programaticamente sem passar pelo registry yaml. Existe `docs/propostas/linking/007768_dirpf-05127373122-2025_retif_conflito.md` que confirma origem na sprint 48 de linking.

## Hipóteses de rota alternativa

H1 -- **Conversor .DEC -> JSON estruturado**: investigar se algum extrator existente (`src/extractors/*irpf*` ou similar) já lê .DEC. Se sim, o ritual passa a confrontar prova artesanal (gerada a partir de PDF da declaração entregue, paralela ao .DEC) vs output do extrator.

H2 -- **Pacote IRPF como produto, não tipo**: dirpf_retif pode ser melhor modelado como agregação periódica (1 declaração/ano) e não como tipo de documento individual. Caberia ao Épico 4 (Pacote IRPF) do ROADMAP, não ao Épico 1 (graduação por tipo).

H3 -- **Excluir do dossiê graduacao_tipos.json**: se H1/H2 falharem, remover dirpf_retif do JSON global e fechar seu dossiê como `STATUS: NAO_APLICAVEL_AO_RITUAL`, anotando isso no `data/output/graduacao_tipos.json`. Isso evita poluir métricas "PENDENTE" com casos não-cobertos pelo ritual.

## Entregável

Decidir entre H1, H2 ou H3 e implementar.

## Acceptance

- Se H1: extrator lê .DEC e popula campos canônicos do schema; prova artesanal feita a partir de PDF da declaração (em separado do .DEC); `comparar` retorna GRADUADO_OK para >= 2 amostras.
- Se H2: spec movida para Épico 4, dossiê dirpf_retif removido de `graduacao_tipos.json`.
- Se H3: novo status `NAO_APLICAVEL_AO_RITUAL` adicionado em `scripts/dossie_tipo.py`; `data/output/graduacao_tipos.json` mostra que dirpf_retif está fora do ritual; métricas globais não contam mais como PENDENTE.

## Não-objetivos

- Não forçar leitura multimodal de .DEC -- ritual seria distorcido se eu inventar leitura.
- Não buscar amostras adicionais "para chegar a 2" -- problema raiz é estrutural, não numérico.

## Padrões aplicáveis

- **(k)** Hipótese da spec não é dogma -- bloqueio veio de grep + tentativa real, não de teoria.
- **(gg)** Cache sintético é placeholder honesto -- não vou gerar cache "artesanal" se não posso ler o documento.

---

*"Tipo sem rito é exceção; exceção sem espec é dívida silenciosa." -- princípio da inviabilidade declarada*
