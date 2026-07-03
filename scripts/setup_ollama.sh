#!/usr/bin/env bash
# Installation et demarrage d'Ollama en local (hors Docker), a titre indicatif.
# Dans Codespaces, executer ce script puis lancer le backend/frontend.
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen2.5:0.5b}"

echo "==> Installation d'Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

echo "==> Demarrage du serveur Ollama (arriere-plan)"
ollama serve >/tmp/ollama.log 2>&1 &

echo "==> Attente du serveur..."
until ollama list >/dev/null 2>&1; do sleep 2; done

echo "==> Telechargement du modele ${MODEL}"
ollama pull "${MODEL}"

echo "==> Ollama pret. Modele disponible : ${MODEL}"
