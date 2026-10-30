#!/bin/bash
set -e

echo "=== Post create devcontainer ==="

# Load local environment variables if present (not committed)
# Source in current shell AND persist for future terminal sessions
if [ -f .devcontainer/.env.local ]; then
  echo "Loading local environment variables from .devcontainer/.env.local"
  set -a
  # shellcheck source=/dev/null
  source .devcontainer/.env.local
  set +a

  # Persist for all future terminal sessions (terminals open in the workspace root)
  LOADER_LINE='[ -f .devcontainer/.env.local ] && set -a && source .devcontainer/.env.local && set +a'
  if ! grep -q ".env.local" ~/.bashrc 2>/dev/null; then
    {
      echo ""
      echo "# Auto-load local env vars from devcontainer"
      echo "$LOADER_LINE"
    } >> ~/.bashrc
  fi
fi

# Fix saml2aws issue
if [ -f /home/codespace/.saml2aws ]; then
  echo "Fix saml2aws home directory"
  sudo cp -r /home/codespace/.saml2aws /home/vscode/
  sudo chown -R vscode:vscode /home/vscode/.saml2aws
fi

# Créer le symlink python → python3 (chemin fixe de la feature devcontainer)
sudo ln -sf /usr/local/python/current/bin/python3 /usr/local/bin/python

python -m venv --clear .venv
# shellcheck source=/dev/null
. .venv/bin/activate
pip install --upgrade pip
pip install -r .devcontainer/requirements.txt -r app_src/app/lambdas/requirements.txt -r app_src/app/lambdas_container/libreoffice_converter/requirements.txt

# Install pre-commit (non-fatal if not yet available)
if command -v pre-commit &>/dev/null; then
  pre-commit install --hook-type pre-commit --hook-type commit-msg --install-hooks
else
  echo "[WARN] pre-commit not found, skipping hook installation"
fi

echo "Done"
