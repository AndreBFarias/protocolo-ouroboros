# Sprint IRPF-02.x -- Ranking top-1 do linking_medico precisa peso para tag_irpf

> **Slug ASCII**: `irpf_02_x_ranking_top1_tag_irpf`. Texto livre: "IRPF-02.x".

**Origem**: achado de validação ao commitar IRPF-02 em 2026-05-01.
Teste `test_dois_candidatos_pega_o_de_score_mais_alto` em
`tests/test_linking_medico.py` falha quando 2 transações candidatas
têm `quem_bate=True` mas apenas uma delas carrega
`tag_irpf=dedutivel_medico`. O ranking atual escolhe a errada porque
o bonus de tag_irpf (0.10) e o bonus quem_bate (0.10) caem em casos
onde a fraca já tem score 1.0 por outra rota e o desempate vai pelo
order de inserção, não pelo bonus combinado.

**Prioridade**: P2
**Onda**: 4 (IRPF granular)
**Esforço estimado**: 1-2h
**Depende de**: IRPF-02 (heurística base já entregue).

## Problema

Em `src/transform/linking_medico.py`, dois candidatos com
`quem_bate=True` ambos chegam a score 1.0 (clamp em [0,1]) apesar de
um ter `tag_irpf=dedutivel_medico` que deveria ser sinal forte. O
sort estável devolve o primeiro inserido, não o de tag_irpf.

## Hipótese para validação

O fix natural é remover o clamp ou aumentar o peso do
`tag_irpf_dedutivel` (0.10 -> 0.20) para que o bonus seja
distinguível em transações que já estão saturadas por outras rotas.
Validar com grep no código antes de codar (padrão (k) BRIEF).

## Critério de pronto

- [ ] `pytest tests/test_linking_medico.py::test_dois_candidatos_pega_o_de_score_mais_alto`
      passa sem `xfail`.
- [ ] Marker `@pytest.mark.xfail(...)` removido do teste.
- [ ] Sem regressão em `make test`.
- [ ] `make lint` exit 0.

## Decisão diferida

Trade-off entre remover clamp ou aumentar peso. Decidir na sprint.

*"Cada dedução médica é um direito reconhecido pelo grafo." -- princípio operacional do Protocolo Ouroboros*
