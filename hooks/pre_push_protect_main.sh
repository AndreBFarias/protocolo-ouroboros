#!/usr/bin/env bash
# Hook pre-push: bloqueia push direto para main.
# Forca uso de PRs para merge em main (redundante com branch protection remota).
# Instalacao: pre-commit install --hook-type pre-push

set -euo pipefail

protected_branch='main'

while read -r local_ref local_sha remote_ref remote_sha; do
    remote_branch=$(echo "$remote_ref" | sed -e 's,.*/\(.*\),\1,')
    if [ "$remote_branch" = "$protected_branch" ]; then
        echo "[ERRO] Push direto para main bloqueado."
        echo "       Crie um PR a partir de uma branch de trabalho:"
        echo "       git push origin feature/nome && gh pr create --base main"
        exit 1
    fi
done

exit 0

# "A disciplina e a ponte entre objetivos e realizacao." -- Jim Rohn
