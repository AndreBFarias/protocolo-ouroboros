#!/usr/bin/env bash
# Rejeita uma proposta: move para _rejeitadas/, registra motivo e atualiza
# DIARIO_MELHORIAS.md.
#
# Uso: bash scripts/supervisor_rejeitar.sh <caminho_da_proposta> "<motivo>"

set -euo pipefail
cd "$(dirname "$0")/.."

PROPOSTA="${1:-}"
MOTIVO="${2:-}"
if [ -z "$PROPOSTA" ] || [ ! -f "$PROPOSTA" ] || [ -z "$MOTIVO" ]; then
    echo "Uso: $0 <caminho_da_proposta> \"<motivo>\"" >&2
    echo "  ex.: $0 docs/propostas/regra/2026-04-20_x.md \"regex muito frouxa\"" >&2
    exit 1
fi

for campo in "^id:" "^tipo:" "^data:" "^status:"; do
    if ! grep -qE "$campo" "$PROPOSTA"; then
        echo "erro: proposta sem campo obrigatório ($campo) em $PROPOSTA" >&2
        exit 2
    fi
done

if grep -qE "^status:\s*(aprovada|rejeitada)" "$PROPOSTA"; then
    echo "aviso: proposta já tem status terminal em $PROPOSTA; nada a fazer" >&2
    exit 0
fi

ID=$(awk -F': ' '/^id:/ {print $2; exit}' "$PROPOSTA" | tr -d '[:space:]')
TIPO=$(awk -F': ' '/^tipo:/ {print $2; exit}' "$PROPOSTA" | tr -d '[:space:]')
DATA_HOJE=$(date -I)

DIR_REJ="docs/propostas/${TIPO}/_rejeitadas"
mkdir -p "$DIR_REJ"
DESTINO="${DIR_REJ}/${ID}.md"

if [ -f "$DESTINO" ]; then
    echo "erro: destino já existe em $DESTINO" >&2
    exit 4
fi

TMP=$(mktemp)
awk -v data="$DATA_HOJE" -v mot="$MOTIVO" '
    /^status: aberta/ { print "status: rejeitada"; next }
    /^---$/ && !inserted && seen {
        print "rejeitada_em: " data
        print "motivo_rejeicao: \"" mot "\""
        inserted=1
    }
    /^---$/ { seen=1 }
    { print }
' "$PROPOSTA" > "$TMP"
mv "$TMP" "$PROPOSTA"

sed -i "s|\\*\\*Rejeitada em:\\*\\* (preencher ao rejeitar)|**Rejeitada em:** $DATA_HOJE|" "$PROPOSTA"
sed -i "s|\\*\\*Motivo:\\*\\* (se rejeitada)|**Motivo:** $MOTIVO|" "$PROPOSTA"

mv "$PROPOSTA" "$DESTINO"

# Diário
DIARIO="docs/DIARIO_MELHORIAS.md"
if grep -qF "## $DATA_HOJE" "$DIARIO"; then
    awk -v data="$DATA_HOJE" -v id="$ID" -v tipo="$TIPO" -v destino="$DESTINO" -v mot="$MOTIVO" '
        /^## / && $2 == data && !inserted {
            print
            print ""
            print "### " id " (rejeitada)"
            print ""
            print "- **tipo:** " tipo "  **status:** rejeitada"
            print "- **motivo:** " mot
            print "- **arquivo:** `" destino "`"
            print ""
            inserted=1
            next
        }
        { print }
    ' "$DIARIO" > "$TMP"
    mv "$TMP" "$DIARIO"
else
    awk -v data="$DATA_HOJE" -v id="$ID" -v tipo="$TIPO" -v destino="$DESTINO" -v mot="$MOTIVO" '
        /^---$/ && !inserted && seen {
            print "## " data
            print ""
            print "### " id " (rejeitada)"
            print ""
            print "- **tipo:** " tipo "  **status:** rejeitada"
            print "- **motivo:** " mot
            print "- **arquivo:** `" destino "`"
            print ""
            print "---"
            inserted=1
            next
        }
        /^---$/ { seen=1 }
        { print }
    ' "$DIARIO" > "$TMP"
    mv "$TMP" "$DIARIO"
fi

echo "Proposta rejeitada: $DESTINO"
echo "Motivo: $MOTIVO"
echo "Diário atualizado: $DIARIO"

# "Rejeitar cedo evita corrigir tarde." -- princípio da economia de esforço
