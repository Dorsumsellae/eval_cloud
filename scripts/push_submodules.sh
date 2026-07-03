#!/usr/bin/env bash
##############################################################################
# Cree les depots GitHub des submodules (backend, frontend) et pousse tout.
#
# Prerequis :
#   - gh (GitHub CLI) installe            https://cli.github.com/
#   - gh authentifie                      gh auth login
#
# A lancer depuis Git Bash, a la racine du projet ou via son chemin :
#   bash scripts/push_submodules.sh
##############################################################################
set -euo pipefail

# Doit correspondre au owner du depot parent (github.com/<OWNER>/eval_cloud).
# Les URLs relatives de .gitmodules (../eval_cloud-backend.git) se resolvent
# contre ce owner : les noms de repos ci-dessous doivent donc rester exacts.
OWNER="Dorsumsellae"
VISIBILITY="public"          # "public" ou "private"
BACKEND_REPO="eval_cloud-backend"
FRONTEND_REPO="eval_cloud-frontend"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

command -v gh >/dev/null 2>&1 || {
  echo "ERREUR : gh (GitHub CLI) n'est pas installe. Voir https://cli.github.com/"
  exit 1
}
gh auth status >/dev/null 2>&1 || {
  echo "ERREUR : gh n'est pas authentifie. Lance d'abord : gh auth login"
  exit 1
}

echo "==> Creation + push du submodule backend ($OWNER/$BACKEND_REPO)"
gh repo create "$OWNER/$BACKEND_REPO" --"$VISIBILITY" \
  --source=backend --remote=origin --push

echo "==> Creation + push du submodule frontend ($OWNER/$FRONTEND_REPO)"
gh repo create "$OWNER/$FRONTEND_REPO" --"$VISIBILITY" \
  --source=frontend --remote=origin --push

echo "==> Push du depot parent (commit de conversion en submodules)"
git push origin HEAD

echo ""
echo "Termine. Verification recommandee :"
echo "  git clone --recursive https://github.com/$OWNER/eval_cloud.git /tmp/verif_clone"
