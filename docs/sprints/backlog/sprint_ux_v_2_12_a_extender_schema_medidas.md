---
id: UX-V-2.12.A
titulo: Estender schema medidas para gordura/pressão/frequência/sono
status: backlog
prioridade: media
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-2.12]
co_executavel_com: []
esforco_estimado_horas: 4
origem: achado colateral durante UX-V-2.12 -- mockup 24-medidas.html cita 6 metricas
        (peso/gordura/cintura/pressao/freq.card./sono) mas schema atual de medidas.json
        cobre apenas peso/cintura/quadril/peito/braco/coxa (medidas antropometricas).
mockup: novo-mockup/mockups/24-medidas.html
---

# Sprint UX-V-2.12.A -- Estender schema medidas para fisiológicas

## Contexto

O mockup 24-medidas.html mostra 6 cards corporais que misturam medidas
antropométricas (peso, cintura) com fisiológicas (gordura corporal %,
pressão sistólica/diastólica, frequência cardíaca rep, sono médio). O
schema atual de `medidas.json` (mobile_cache) só cobre antropométricas:
`peso, cintura, quadril, peito, braco, coxa`.

A sprint UX-V-2.12 manteve retrocompatibilidade do schema atual e
exibe os 6 campos antropométricos. Esta sprint-filha estende o schema
para incluir as métricas fisiológicas e atualiza extrator mobile +
página dashboard para renderizar os campos novos quando presentes.

## Páginas afetadas

- `src/mobile_cache/varrer_vault.py` (escrita do cache).
- `src/dashboard/paginas/be_medidas.py` (leitura + grid).
- `tests/test_be_resto.py` (atualizar fixture).
- `tests/fixtures/vault_sintetico/.ouroboros/cache/medidas.json` (amostra).

## Objetivo

1. Adicionar campos opcionais ao schema: `gordura_pct`, `pressao_sis`,
   `pressao_dia`, `freq_card`, `sono_horas`.
2. Estender `CAMPOS` e `CORES_METRICAS` em be_medidas.py com os novos.
3. Mockup-paridade: cards na ordem do 24-medidas.html.
4. Tabela histórico exibe colunas adicionais quando dados existem.

## Validação ANTES (padrão (k))

```bash
grep -n "peso.*cintura.*quadril" src/mobile_cache/
ls tests/fixtures/vault_sintetico/.ouroboros/cache/medidas.json
```

## Não-objetivos (padrão (t))

- NÃO implementar integração Mi Fit/Garmin (sprint separada).
- NÃO mexer em frontmatter de notas de medida.

## Proof-of-work (padrão (u))

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_resto.py -q
.venv/bin/python -c "from src.dashboard.paginas import be_medidas; \
  print(be_medidas.CAMPOS)"  # esperado: 6 antropométricas + 5 fisiológicas
```

Validação visual em `cluster=Bem-estar&tab=Medidas` com fixture estendida.

## Critério de aceitação

1. CAMPOS estendido com `gordura_pct, pressao_sis, freq_card, sono_horas`.
2. Fixture sintética inclui amostras com novos campos.
3. Tests be_resto verde após atualização.
4. Mockup-paridade visual confirmada por screenshot.

## Referência

- Sprint-pai: UX-V-2.12.
- VALIDATOR_BRIEF: (a)/(k)/(o)/(t)/(u).

*"Cada métrica nova é um passo a mais de paridade." -- UX-V-2.12.A*
