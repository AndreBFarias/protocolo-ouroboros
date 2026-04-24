# Feather Icons -- NOTICE

Ícones SVG inline em `src/dashboard/componentes/icons.py` são derivados do
projeto **Feather Icons**.

- Projeto upstream: https://github.com/feathericons/feather
- Site oficial: https://feathericons.com
- Licença: MIT

Os 11 SVGs reproduzidos neste repositório (`search`, `check-circle`,
`alert-triangle`, `alert-circle`, `info`, `x`, `zoom-in`, `download`,
`external-link`, `filter`, `calendar`) vêm da release 4.x e foram copiados
literalmente do upstream, com dois placeholders (`{size}` e `{color}`)
adicionados para parametrização em tempo de render.

Nenhuma modificação estética foi aplicada: viewBox 24x24, stroke-width 2,
stroke-linecap e stroke-linejoin round permanecem originais.

## Texto da licença MIT

```
The MIT License (MIT)

Copyright (c) 2013-2023 Cole Bemis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

## Como atualizar

1. Baixar release nova do repositório upstream (ou clonar).
2. Para cada ícone listado acima, copiar o SVG do diretório `icons/` do
   upstream.
3. Colar no módulo `src/dashboard/componentes/icons.py` preservando ordem
   dos atributos.
4. Trocar `width="24" height="24"` por `width="{size}" height="{size}"` e
   `stroke="currentColor"` por `stroke="{color}"`.
5. Rodar `.venv/bin/pytest tests/test_dashboard_tema.py -q` para garantir
   que o formato `.format(size=..., color=...)` segue funcionando.

## Decisão arquitetural

- **SVG inline, sem dependência:** Feather costuma ser distribuído via npm
  (`feather-icons`) ou CDN. Ambas as opções violam o princípio Local First
  (CLAUDE.md regra #4) do projeto e adicionam custo de runtime. Copiar
  literalmente o SVG (12 linhas cada) é mais simples e mais performático.
- **Por que apenas 11 ícones:** são os suficientes para a Sprint 92c
  (callouts, busca, tracking documental, breadcrumb, exportação, preview,
  filtros, calendário). Novos ícones podem ser adicionados caso a caso
  mantendo esta NOTICE atualizada.
