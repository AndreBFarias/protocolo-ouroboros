---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-13
  title: "Citação filosófica final em 60 arquivos .py novos da branch"
  prioridade: P1
  estimativa: 2h
  onda: C5
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §3.5 (regra 10 do CLAUDE.md violada em 100% dos novos)"
  depende_de: [UX-RD-FIX-01, UX-RD-FIX-02, UX-RD-FIX-03, UX-RD-FIX-04, UX-RD-FIX-05, UX-RD-FIX-06, UX-RD-FIX-07, UX-RD-FIX-08, UX-RD-FIX-09, UX-RD-FIX-10, UX-RD-FIX-11, UX-RD-FIX-12]
  bloqueia: []
  touches:
    - path: scripts/check_citacao_filosofica.py
      reason: "NOVO -- linter que valida regra 10 (todo .py novo tem `# \"frase\" -- Autor` na última linha não-vazia)"
    - path: Makefile
      reason: "linha lint: adicionar 'check_citacao_filosofica.py' antes de 'check_acentuacao.py'"
    - path: 60 arquivos .py listados no §3
      reason: "adicionar citação filosófica final em todos -- regra 10 do CLAUDE.md"
    - path: tests/test_citacao_filosofica.py
      reason: "NOVO -- 1 teste que itera todos .py em src/ e tests/ verificando padrão final"
  forbidden:
    - "Citações repetidas (cada arquivo tem citação distinta -- mantém variedade)"
    - "Adicionar emoji ou caractere fora do PT-BR padrão"
    - "Sobrescrever citação existente em arquivos pre-existentes"
  hipotese:
    - "Auditoria contou 60 arquivos .py adicionados pela branch ux/redesign-v1 (39 em src/, 2 em scripts/, 19 em tests/) -- nenhum tem citação filosófica final no padrão `# \"frase\" -- Autor`. Verificar lista atualizada após FIX-01..12 (podem ter sido criados arquivos novos durante as outras sprints)."
  tests:
    - cmd: ".venv/bin/pytest tests/test_citacao_filosofica.py -v"
      esperado: "PASSED em 100% dos .py de src/ e scripts/"
    - cmd: "make lint"
      esperado: "exit 0 + nova etapa 'check_citacao_filosofica: 0 problema(s) encontrado(s)'"
  acceptance_criteria:
    - "100% dos .py em src/ e scripts/ (incluindo arquivos novos das sprints FIX-01 a FIX-12) têm como última linha não-vazia: `# \"<frase>\" -- <Autor>`"
    - "Tests/ é OPCIONAL (CLAUDE.md regra 10 fala 'arquivo .py novo' -- testes contam? confirmar com dono; default é incluir)"
    - "Scripts/check_citacao_filosofica.py instalado como segundo gate do make lint (depois de ruff, antes de check_acentuacao)"
    - "Cada citação é distinta (sem duplicatas) -- variedade autoral mantida"
    - "Tema da citação tem alguma relação semântica com o conteúdo do arquivo (ex.: arquivo de auditoria/validação tem filósofo da verdade; arquivo de UI tem citação sobre forma)"
  proof_of_work_esperado: |
    .venv/bin/python scripts/check_citacao_filosofica.py --all 2>&1 | tee /tmp/proof_fix_13.log
    echo "EXIT=$?"
    grep -c "OK" /tmp/proof_fix_13.log
    grep "FALHA" /tmp/proof_fix_13.log || echo "zero falhas"
```

---

# Sprint UX-RD-FIX-13 — Citação filosófica em 60 .py

**Status:** BACKLOG — Onda C5 (acabamento). **ÚLTIMA do roteiro.**

## 1. Contexto

Auditoria 2026-05-05 §3.5: a branch `ux/redesign-v1` adicionou **exatamente 60 arquivos** `.py`, **nenhum** com citação filosófica final no padrão `# "frase" -- Autor` (regra 10 do CLAUDE.md, item *"Citação de filósofo como comentário final de todo arquivo .py novo"*).

### Lista canônica dos 60 arquivos (gerada via `git diff --name-status main..HEAD | awk '$1=="A" && $2 ~ /\.py$/ {print $2}' | sort`)

```
1.  scripts/migrar_csv_confianca_opus.py
2.  scripts/smoke_bem_estar.py
3.  src/dashboard/componentes/atalhos_revisor.py
4.  src/dashboard/componentes/atalhos_teclado.py
5.  src/dashboard/componentes/drawer_transacao.py
6.  src/dashboard/componentes/heatmap_humor.py
7.  src/dashboard/componentes/html_utils.py
8.  src/dashboard/componentes/shell.py
9.  src/dashboard/paginas/be_ciclo.py
10. src/dashboard/paginas/be_cruzamentos.py
11. src/dashboard/paginas/be_diario.py
12. src/dashboard/paginas/be_editor_toml.py
13. src/dashboard/paginas/be_eventos.py
14. src/dashboard/paginas/be_hoje.py
15. src/dashboard/paginas/be_humor.py
16. src/dashboard/paginas/be_medidas.py
17. src/dashboard/paginas/be_memorias.py
18. src/dashboard/paginas/be_privacidade.py
19. src/dashboard/paginas/be_recap.py
20. src/dashboard/paginas/be_rotina.py
21. src/dashboard/paginas/extracao_tripla.py
22. src/dashboard/paginas/inbox.py
23. src/dashboard/paginas/skills_d7.py
24. src/dashboard/paginas/styleguide.py
25. src/exports/__init__.py
26. src/exports/pacote_irpf.py
27. src/intake/inbox_reader.py
28. src/mobile_cache/_base.py
29. src/mobile_cache/alarmes.py
30. src/mobile_cache/ciclo.py
31. src/mobile_cache/contadores.py
32. src/mobile_cache/diario_emocional.py
33. src/mobile_cache/escrever_diario.py
34. src/mobile_cache/escrever_evento.py
35. src/mobile_cache/escrever_humor.py
36. src/mobile_cache/eventos.py
37. src/mobile_cache/marcos.py
38. src/mobile_cache/medidas.py
39. src/mobile_cache/tarefas.py
40. src/mobile_cache/treinos.py
41. src/mobile_cache/varrer_vault.py
42. tests/test_analise_redesign.py
43. tests/test_be_diario_eventos.py
44. tests/test_be_hoje_humor.py
45. tests/test_be_resto.py
46. tests/test_busca_catalogacao_redesign.py
47. tests/test_categorias_redesign.py
48. tests/test_completude_revisor_redesign.py
49. tests/test_contas_pagamentos_redesign.py
50. tests/test_extracao_tripla.py
51. tests/test_extrato_redesign.py
52. tests/test_inbox_real.py
53. tests/test_irpf_metas_redesign.py
54. tests/test_mobile_cache_bem_estar.py
55. tests/test_projecoes_redesign.py
56. tests/test_shell_redesign.py
57. tests/test_sistema_redesign.py
58. tests/test_tema_css_redesign.py
59. tests/test_tema_tokens_redesign.py
60. tests/test_visao_geral_redesign.py
```

**Atualização**: após FIX-01 a FIX-12 mergeadas, a lista pode crescer. Re-rodar o comando para obter a lista atualizada antes de aplicar citações. Adições previstas:
- FIX-07 cria `src/dashboard/componentes/glyphs.py` + `tests/test_glyphs.py` (+2)
- FIX-09 cria `src/dashboard/tema_plotly.py` + `tests/test_tema_plotly.py` (+2)
- FIX-10 cria 5 páginas (be_treinos, be_marcos, be_alarmes, be_contadores, be_tarefas) + 2 testes (+7)
- FIX-12 cria `tests/test_acessibilidade.py` (+1)
- Possíveis: tests/test_breadcrumb_clicavel.py, test_h1_unico_por_tela.py, test_tema_css.py, test_material_symbols.py, test_extrato_kpi_despesa.py, test_be_paginas_novas.py, test_be_12abas_consistente.py, test_deeplink_bemestar.py, test_deeplink_orfaos.py, test_tipografia_escala.py, test_citacao_filosofica.py (+11)

**Estimativa final**: ~83 arquivos .py novos quando FIX-13 rodar.

### Padrão antigo do projeto (referência)

```python
# src/pipeline.py
...
# "A verdadeira sabedoria está em reconhecer a própria ignorância." -- Sócrates
```

Esta sprint **fecha o ciclo** instalando:

1. Linter `check_citacao_filosofica.py` para impedir regressão futura.
2. Citação em todos os 60 arquivos novos (e em quaisquer outros adicionados nas FIX-01..12).
3. Teste pytest que valida o invariante.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) listar .py novos na branch (atualizado pós-merge das FIX)
git diff --name-status main..HEAD | awk '$1=="A" && $2 ~ /\.py$/ {print $2}' | tee /tmp/py_novos.txt
wc -l /tmp/py_novos.txt   # >=60 (pode ser maior depois de FIX-07 e FIX-09 criarem novos)

# 2) verificar quantos JÁ têm citação no padrão "frase" -- Autor
COM=0; SEM=0
while read f; do
    ULT=$(tail -3 "$f" 2>/dev/null)
    if echo "$ULT" | grep -qE '^#.*"\..*"\s*--' ; then COM=$((COM+1)); else SEM=$((SEM+1)); fi
done < /tmp/py_novos.txt
echo "COM=$COM SEM=$SEM"
```

## 3. Tarefas

1. Rodar hipótese.
2. Criar `scripts/check_citacao_filosofica.py`:
   ```python
   #!/usr/bin/env python3
   """Valida regra 10 do CLAUDE.md: todo .py de src/ e scripts/ tem
   citação filosófica final no padrão `# "<frase>" -- <Autor>`.
   
   Uso: python scripts/check_citacao_filosofica.py --all
        python scripts/check_citacao_filosofica.py src/dashboard/paginas/be_hoje.py
   """
   from __future__ import annotations
   import argparse, re, sys
   from pathlib import Path

   PADRAO = re.compile(r'^#\s*"[^"]+\.\s*"\s*--\s*\w+', re.MULTILINE)

   def valida_arquivo(p: Path) -> tuple[bool, str]:
       try:
           texto = p.read_text(encoding="utf-8")
       except Exception as e:
           return False, f"erro de leitura: {e}"
       linhas_nao_vazias = [l.rstrip() for l in texto.splitlines() if l.strip()]
       if not linhas_nao_vazias:
           return False, "arquivo vazio"
       ultimas3 = "\n".join(linhas_nao_vazias[-3:])
       if PADRAO.search(ultimas3):
           return True, "OK"
       return False, "ausente ou fora do padrão"

   def main() -> int:
       parser = argparse.ArgumentParser()
       parser.add_argument("--all", action="store_true")
       parser.add_argument("paths", nargs="*")
       args = parser.parse_args()
       if args.all:
           alvos = list(Path("src").rglob("*.py")) + list(Path("scripts").rglob("*.py"))
       else:
           alvos = [Path(p) for p in args.paths]
       falhas = []
       for p in alvos:
           ok, msg = valida_arquivo(p)
           print(f'{"OK" if ok else "FALHA"} {p}: {msg}')
           if not ok: falhas.append(p)
       print(f"\nResumo: {len(alvos)-len(falhas)} OK / {len(falhas)} falha")
       return 1 if falhas else 0

   if __name__ == "__main__":
       sys.exit(main())

   # "O fim de cada coisa é melhor do que o seu princípio." -- Eclesiastes (Bíblia)
   ```
3. Atualizar `Makefile` linha do target `lint`:
   ```makefile
   lint: ## Verifica código com ruff + acentuação + cobertura total D7 + citação filosófica
       .venv/bin/ruff check src/ tests/ scripts/
       .venv/bin/python scripts/check_citacao_filosofica.py --all
       .venv/bin/python scripts/check_acentuacao.py --all
       .venv/bin/python scripts/check_cobertura_total.py
   ```
4. Adicionar citação em cada um dos 60 arquivos. **Diretrizes**:
   - Cada citação tem que ter relação temática com o conteúdo do arquivo.
   - Sem repetições (catalogar para evitar).
   - Padrão: `# "Frase com pontuação final." -- Autor` (uma linha, no fim do arquivo após `\n\n`).
   - **Sugestões temáticas**:
     - Páginas Bem-estar (`be_*.py`): filósofos do corpo/cuidado (Foucault, Schopenhauer, Sêneca, Lao-Tsé)
     - Componentes UI (`shell.py`, `glyphs.py`, `drawer_transacao.py`): filósofos da forma (Eric Gill, Bauhaus, Mies, Wittgenstein)
     - Tema/CSS (`tema*.py`): filósofos da estética (Kant, Hegel, Adorno)
     - Auditoria/Validação (`exports/`, `revisor*`): filósofos da verdade (Tukey, Popper, Bacon)
     - Mobile cache: filósofos da memória (Bergson, Halbwachs, Proust)
     - Tests (opcional): filósofos do método (Descartes, Quine)
5. Para automação parcial, criar script `scripts/_aplicar_citacoes.py` que lê uma lista YAML de citações sugeridas e gera o patch de Edit em cada arquivo.

**Sugestões temáticas por categoria (60 arquivos atuais; ajustar para os ~83 finais)**:

| Categoria | Filósofos sugeridos | Arquivos |
|---|---|---|
| Páginas Bem-estar (be_*.py) | Foucault, Schopenhauer, Sêneca, Lao-Tsé, Epicuro, Bergson, Hannah Arendt, Marco Aurélio, Han, Pessoa | 12 arquivos (be_ciclo, be_cruzamentos, be_diario, be_editor_toml, be_eventos, be_hoje, be_humor, be_medidas, be_memorias, be_privacidade, be_recap, be_rotina) |
| Páginas Documentos/Inbox/Skills (paginas/*.py) | Tukey, Popper, Bacon, Cicero, Quintiliano | 4 (extracao_tripla, inbox, skills_d7, styleguide) |
| Componentes UI (componentes/*.py) | Eric Gill, Mies van der Rohe, Bauhaus, Wittgenstein, Saul Steinberg | 6 (atalhos_revisor, atalhos_teclado, drawer_transacao, heatmap_humor, html_utils, shell) |
| Mobile cache (mobile_cache/*.py) | Bergson, Halbwachs, Proust, Locke, Hume, Borges | 14 (todos os _base, alarmes, ciclo, etc.) |
| Exports/Intake (exports/*, intake/*) | Heráclito, Tucídides, Boécio | 3 |
| Scripts (scripts/*) | Sêneca, Marco Aurélio, Confúcio | 2 |
| Tests (tests/*) | Descartes, Quine, Russell, Lakatos, Popper | 19 |

Exemplo de citação por arquivo (a IA executora deve **diversificar**, não repetir autor):

- `be_ciclo.py`: `# "O corpo é o tempo feito carne." -- Lao-Tsé (paráfrase)`
- `be_humor.py`: `# "Toda emoção tem ritmo, mesmo as que ainda não nomeamos." -- Bergson (paráfrase)`
- `tema_plotly.py`: `# "A graça do desenho está em saber o que omitir." -- Mies van der Rohe`
- `test_acessibilidade.py`: `# "O acesso é o primeiro direito; sem ele, todos os outros são promessa." -- Hannah Arendt`
6. Criar `tests/test_citacao_filosofica.py`:
   ```python
   from pathlib import Path
   from scripts.check_citacao_filosofica import valida_arquivo

   def test_todos_py_de_src_tem_citacao():
       falhas = []
       for p in Path("src").rglob("*.py"):
           ok, msg = valida_arquivo(p)
           if not ok: falhas.append((str(p), msg))
       assert not falhas, f'{len(falhas)} arquivos sem citação: {falhas[:5]}'

   def test_scripts_tem_citacao():
       falhas = []
       for p in Path("scripts").rglob("*.py"):
           ok, msg = valida_arquivo(p)
           if not ok: falhas.append(str(p))
       assert not falhas, f'scripts sem citação: {falhas}'
   ```
7. Rodar gauntlet (§6).

## 4. Anti-débito

- Se algum arquivo tem citação mas em padrão diferente (ex.: `# "frase" -- Autor.` com ponto antes do --): atualizar regex em `check_citacao_filosofica.py` para aceitar variações comuns OU normalizar o conteúdo. **NÃO** acumular padrões diferentes.
- Se aparecer arquivo .py auto-gerado (ex.: `__pycache__`): excluir do scan.

## 5. Validação visual

Não aplicável (sprint é só comentários no fim de arquivos .py).

## 6. Gauntlet

```bash
make lint                                              # exit 0 (3 etapas: ruff + citacao + acentuacao)
make smoke                                             # 10/10
.venv/bin/pytest tests/test_citacao_filosofica.py -v   # 2/2
.venv/bin/pytest tests/ -q --tb=no                     # baseline >=2520

# Validação manual: spot-check em 5 arquivos
for f in $(git diff --name-status main..HEAD | awk '$1=="A" && $2 ~ /\.py$/ {print $2}' | head -5); do
    echo "=== $f ==="; tail -3 "$f"
done
```

---

*"O fim de cada coisa é melhor do que o seu princípio." -- Eclesiastes*
