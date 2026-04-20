#!/usr/bin/env bash
# Cria esqueleto de proposta nova em docs/propostas/<tipo>/<yyyy-mm-dd>_<slug>.md
# usando o template correspondente.
#
# Uso: bash scripts/supervisor_proposta_nova.sh <tipo> <slug>
#   tipos: regra | classificacao | linking | resolver | categoria_item  # noqa: accent
#   slug:  kebab-case sem acentos, sem espaços

set -euo pipefail
cd "$(dirname "$0")/.."

TIPO="${1:-}"
SLUG="${2:-}"

if [ -z "$TIPO" ] || [ -z "$SLUG" ]; then
    echo "Uso: $0 <tipo> <slug>" >&2
    echo "  tipos: regra | classificacao | linking | resolver | categoria_item" >&2  # noqa: accent
    echo "  slug:  kebab-case, sem espaços nem acentos (ex.: neoenergia-v2)" >&2
    exit 1
fi

# Normalizar slug: espaços viram hífen, remove acentos básicos, minúsculo
SLUG_NORM=$(echo "$SLUG" \
    | tr '[:upper:]' '[:lower:]' \
    | tr ' ' '-' \
    | sed 's/[àáâãä]/a/g; s/[éêë]/e/g; s/[íî]/i/g; s/[óôõö]/o/g; s/[úû]/u/g; s/ç/c/g' \
    | tr -cd 'a-z0-9_-')

if [ "$SLUG_NORM" != "$SLUG" ]; then
    echo "nota: slug normalizado de '$SLUG' para '$SLUG_NORM'" >&2
fi

DATA=$(date -I)
ID="${DATA}_${SLUG_NORM}"
DESTINO="docs/propostas/${TIPO}/${ID}.md"

# Template por tipo; regra/resolver/categoria_item compartilham PROPOSTA_REGRA
case "$TIPO" in
    regra|resolver|categoria_item)
        TEMPLATE="docs/templates/PROPOSTA_REGRA.md"
        ;;
    classificacao)
        TEMPLATE="docs/templates/PROPOSTA_CLASSIFICACAO.md"
        ;;
    linking)
        TEMPLATE="docs/templates/PROPOSTA_LINKING.md"
        ;;
    *)
        echo "erro: tipo desconhecido '$TIPO'" >&2
        echo "  válidos: regra | classificacao | linking | resolver | categoria_item" >&2  # noqa: accent
        exit 2
        ;;
esac

if [ ! -f "$TEMPLATE" ]; then
    echo "erro: template não encontrado em $TEMPLATE" >&2
    exit 3
fi

mkdir -p "$(dirname "$DESTINO")"

if [ -f "$DESTINO" ]; then
    echo "erro: proposta já existe em $DESTINO" >&2
    exit 4
fi

# Copia template e substitui placeholders do frontmatter
cp "$TEMPLATE" "$DESTINO"
sed -i "s|<yyyy-mm-dd>_<slug>|$ID|g; s|<yyyy-mm-dd>|$DATA|g" "$DESTINO"

# tipo vem pré-preenchido no template -- força pra o tipo correto se usuário usou resolver/categoria_item
sed -i "s|^tipo: regra|tipo: $TIPO|" "$DESTINO"

echo "Proposta aberta: $DESTINO"
echo
echo "Próximo passo:"
echo "  1. Editar $DESTINO preenchendo Contexto, Diff, Justificativa e Teste."
echo "  2. Ao finalizar: bash scripts/supervisor_aprovar.sh $DESTINO"

# "A proposta que não se escreve, não se aprova." -- princípio do registro
