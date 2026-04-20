#!/usr/bin/env bash
# Aprova uma proposta: valida frontmatter, move para _aprovadas/, registra em
# DIARIO_MELHORIAS.md e imprime guidance para o próximo commit.
#
# Uso: bash scripts/supervisor_aprovar.sh <caminho_da_proposta>

set -euo pipefail
cd "$(dirname "$0")/.."

PROPOSTA="${1:-}"
if [ -z "$PROPOSTA" ] || [ ! -f "$PROPOSTA" ]; then
    echo "Uso: $0 <caminho_da_proposta>" >&2
    echo "  ex.: $0 docs/propostas/regra/2026-04-20_neoenergia.md" >&2
    exit 1
fi

# Validar frontmatter mínimo
for campo in "^id:" "^tipo:" "^data:" "^status:"; do
    if ! grep -qE "$campo" "$PROPOSTA"; then
        echo "erro: proposta sem campo obrigatório ($campo) em $PROPOSTA" >&2
        exit 2
    fi
done

# Validar que ainda está aberta (idempotência -- rodar 2x não re-aprova)
if grep -qE "^status:\s*(aprovada|rejeitada)" "$PROPOSTA"; then
    echo "aviso: proposta já tem status terminal em $PROPOSTA; nada a fazer" >&2
    exit 0
fi

# Validar seções obrigatórias
for sec in "## Contexto" "## Justificativa" "## Decisão humana"; do
    if ! grep -qF "$sec" "$PROPOSTA"; then
        echo "erro: proposta sem seção '$sec'" >&2
        exit 3
    fi
done

ID=$(awk -F': ' '/^id:/ {print $2; exit}' "$PROPOSTA" | tr -d '[:space:]')
TIPO=$(awk -F': ' '/^tipo:/ {print $2; exit}' "$PROPOSTA" | tr -d '[:space:]')
DATA_HOJE=$(date -I)

# Destino: docs/propostas/<tipo>/_aprovadas/<id>.md
DIR_APROVADAS="docs/propostas/${TIPO}/_aprovadas"
mkdir -p "$DIR_APROVADAS"
DESTINO="${DIR_APROVADAS}/${ID}.md"

if [ -f "$DESTINO" ]; then
    echo "erro: destino já existe em $DESTINO -- possível duplicata" >&2
    exit 4
fi

# Atualizar frontmatter: status + aprovada_em
# Usa awk pra preservar formato; sed -i só no status
TMP=$(mktemp)
awk -v data="$DATA_HOJE" '
    /^status: aberta/ { print "status: aprovada"; next }
    /^---$/ && !inserted && seen { print "aprovada_em: " data; inserted=1 }
    /^---$/ { seen=1 }
    { print }
' "$PROPOSTA" > "$TMP"
mv "$TMP" "$PROPOSTA"

# Preencher "Aprovada em:" no rodapé se estiver vazio
sed -i "s|\\*\\*Aprovada em:\\*\\* (preencher ao aprovar)|**Aprovada em:** $DATA_HOJE|" "$PROPOSTA"

# Mover
mv "$PROPOSTA" "$DESTINO"

# Registrar no diário -- insere nova entrada ANTES da entrada mais recente
# (entradas novas ficam no topo da data atual)
DIARIO="docs/DIARIO_MELHORIAS.md"
if [ ! -f "$DIARIO" ]; then
    echo "aviso: $DIARIO ausente; criando agora" >&2
    cat > "$DIARIO" <<EOF
# Diário de Melhorias -- Protocolo Ouroboros

(entradas novas cronologicamente acima da linha abaixo)

---
EOF
fi

# Procura cabeçalho da data de hoje; cria se ausente
if grep -qF "## $DATA_HOJE" "$DIARIO"; then
    # Insere entrada sob a data de hoje (logo após a linha "## DATA")
    awk -v data="$DATA_HOJE" -v id="$ID" -v tipo="$TIPO" -v destino="$DESTINO" '
        /^## / && $2 == data && !inserted {
            print
            print ""
            print "### " id " (aprovada)"
            print ""
            print "- **tipo:** " tipo "  **status:** aprovada"
            print "- **arquivo:** `" destino "`"
            print ""
            inserted=1
            next
        }
        { print }
    ' "$DIARIO" > "$TMP"
    mv "$TMP" "$DIARIO"
else
    # Cria bloco de data novo no topo (antes da primeira ---)
    awk -v data="$DATA_HOJE" -v id="$ID" -v tipo="$TIPO" -v destino="$DESTINO" '
        /^---$/ && !inserted && seen {
            print "## " data
            print ""
            print "### " id " (aprovada)"
            print ""
            print "- **tipo:** " tipo "  **status:** aprovada"
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

echo "Proposta aprovada: $DESTINO"
echo "Diário atualizado: $DIARIO"
echo
echo "Próximo passo:"
echo "  1. Aplicar o diff descrito em $DESTINO em mappings/*.yaml ou src/."
echo "  2. Rodar .venv/bin/pytest para garantir regressão verde."
echo "  3. Commit: feat: absorve proposta $ID"

# "Aprovar é assumir. Rejeitar é preservar." -- princípio da decisão
