"""Catálogo canônico de glyphs para topbar-actions (UX-V-05).

Esta sprint **NÃO** introduz novo sistema visual; apenas formaliza dois
contratos derivados do catálogo já existente em ``componentes/glyphs.py``
(52 SVGs canônicos, paridade 1:1 com ``novo-mockup/_shared/glyphs.js`` --
estabelecido em UX-RD-FIX-07 e consumido pela topbar via UX-U-02).

O que esta sprint adiciona:

1. ``GLYPHS_CANONICOS``: subconjunto curado de IDs SVG do catálogo grande,
   válidos para uso na topbar. Permite a ``topbar_actions.renderizar_grupo_acoes``
   validar IDs em runtime sem ``KeyError`` -- gera ``logging.warning`` graceful.
2. ``ACOES_PARA_GLYPH``: mapeamento semântico ``label -> glyph_id`` que
   serviu de guia ao preencher chamadas de ``renderizar_grupo_acoes`` em
   28 páginas dashboard (referência para auditoria visual cruzada).

Discrepância com a spec: a spec original (UX-V-05) propôs uma camada
ASCII alternativa (``+``, ``^``, ``v``, ``~``...). Hipótese da spec não
era dogma (padrão (k) do VALIDATOR_BRIEF) -- grep mostrou que o sistema
JÁ usa SVG inline desde UX-RD-FIX-07 / UX-U-02 e que 7 páginas já consomem
``"glyph": "<id>"`` apontando para o catálogo SVG. Regredir SVG -> ASCII
violaria padrão (a) (não apagar código funcional). Esta sprint adota o
catálogo SVG existente como fonte canônica.

Origem: UX-V-05.
"""

from __future__ import annotations

from typing import Final

from src.dashboard.componentes.glyphs import GLYPHS as _GLYPHS_SVG

# IDs SVG do catálogo grande considerados válidos para topbar-actions.
# Cada entrada é um ID que existe em ``componentes/glyphs.GLYPHS``; o
# valor associado (descrição curta) serve à auditoria humana e ao log
# de warning quando ID inválido é fornecido.
#
# Subconjunto enxuto -- novos IDs entram aqui após confirmação de que
# o glyph SVG correspondente já existe em ``GLYPHS``.
GLYPHS_CANONICOS: Final[dict[str, str]] = {
    # Adicionar / criar
    "plus": "Adicionar / criar item novo",
    # Atualizar / sincronizar
    "refresh": "Atualizar / recalcular / sincronizar",
    # Importar / exportar
    "upload": "Importar / enviar arquivo",
    "download": "Exportar / baixar",
    # Comparar / diff
    "diff": "Comparar / diferenciar",
    # Validar / aprovar
    "validar": "Validar / salvar / aprovar",
    "check": "Confirmar / marcado",
    # Listas / logs
    "list": "Lista / itens",
    "table": "Tabela / dados",
    # Calendário
    "calendar": "Calendário / data",
    # Documentos
    "docs": "Documento / pasta de documentos",
    "folder": "Pasta",
    # Métricas / análise
    "analise": "Análise / gráfico",
    "trend": "Tendência",
    "metas": "Meta / alvo",
    # Bem-estar
    "heart": "Bem-estar / favorito",
    "mood": "Humor",
    # Gerais
    "search": "Buscar",
    "filter": "Filtrar",
    "eye": "Visualizar",
    "cog": "Configurar",
    "terminal": "Terminal / comando",
    "link": "Link / vínculo",
    "cycle": "Ciclo / período",
    "repeat": "Repetir / sincronizar",
    "sparkle": "Destaque / IA",
    "info": "Informação",
}

# Sanity check em import-time: cada ID validado precisa existir no SVG store.
# Se alguém remover um SVG sem atualizar este catálogo, falha alto e cedo.
_ids_invalidos = sorted(set(GLYPHS_CANONICOS) - set(_GLYPHS_SVG))
if _ids_invalidos:
    raise RuntimeError(
        f"GLYPHS_CANONICOS contém IDs ausentes em componentes/glyphs.GLYPHS: "
        f"{_ids_invalidos}. Adicione ao SVG store ou remova daqui."
    )


# Mapeamento auxiliar: label de ação -> ID de glyph canônico.
# Serve de referência ao adicionar ``glyph`` em chamadas de
# ``renderizar_grupo_acoes``. Não é consumido em runtime -- existe para
# que humanos auditem coerência semântica entre páginas.
ACOES_PARA_GLYPH: Final[dict[str, str]] = {
    # Adicionar / criar
    "Nova meta": "plus",
    "Adicionar conta": "plus",
    "Adicionar tipo": "plus",
    "Novo evento": "plus",
    "Capturar": "plus",
    "Registrar": "plus",
    "Registrar agora": "plus",
    "Registrar dia": "plus",
    "Novo": "plus",
    "Nova regra": "plus",
    "Adicionar": "plus",
    # Salvar / aprovar
    "Salvar": "validar",
    "Salvar humor": "validar",
    "Salvar permissões": "validar",
    "Salvar (commit)": "validar",
    "Salvar cenário": "validar",
    "Salvar validações": "validar",
    "Salvar como bloco do Recap": "validar",
    "Aprovar Opus & avançar": "validar",
    "Marcar pago": "check",
    # Atualizar / recalcular / sincronizar
    "Atualizar": "refresh",
    "Atualizar fila": "refresh",
    "Recalibrar": "refresh",
    "Recalcular": "refresh",
    "Re-gerar agora": "refresh",
    "Reprocessar": "refresh",
    "Recategorizar": "refresh",
    "Sincronizar OFX": "refresh",
    "Random": "refresh",
    # Importar / upload
    "Importar OFX": "upload",
    "Importar Mi Fit": "upload",
    # Exportar / download
    "Exportar": "download",
    "Exportar relatório": "download",
    "Exportar 90d": "download",
    "Exportar gaps": "download",
    "Baixar": "download",
    "Baixar lote": "download",
    "Gerar pacote": "download",
    # Comparar / diff
    "Comparar cenários": "diff",
    "Próxima divergência": "diff",
    # Logs / auditoria / histórico
    "Logs": "list",
    "Audit log": "list",
    "Auditoria": "list",
    "Histórico": "list",
    "Histórico (git log)": "list",
    "Skills D7": "list",
    # Calendário
    "Calendário": "calendar",
    "Hoje": "calendar",
    # Documentos / pastas
    "Abrir pasta": "folder",
    "Diário emocional": "heart",
    # Análise / cruzamentos
    "Cruzamentos": "diff",
    "Heatmap": "analise",
    "Categorias": "list",
    # Validação / revisor
    "Ir para Validação": "validar",
}


def glyph_valido(glyph_id: str | None) -> bool:
    """Retorna True se ``glyph_id`` é válido para topbar-actions.

    ``None`` ou string vazia retornam True (glyph é opcional).
    """
    if not glyph_id:
        return True
    return glyph_id in GLYPHS_CANONICOS


# "O glyph é a primeira leitura; o label é a segunda." -- princípio UX-V-05
