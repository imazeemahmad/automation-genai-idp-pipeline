#!/bin/bash
set -e

echo "=== Post create devcontainer ==="

# Fix saml2aws issue
if [ -f /home/codespace/.saml2aws ]; then
  echo "Fix saml2aws home directory"
  sudo cp -r /home/codespace/.saml2aws /home/vscode/
  sudo chown -R vscode:vscode /home/vscode/.saml2aws
fi

# Créer le symlink python → python3 (chemin fixe de la feature devcontainer)
sudo ln -sf /usr/local/python/current/bin/python3 /usr/local/bin/python

python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r .devcontainer/requirements.txt -r app_src/app/lambdas/requirements.txt

# Install terraform
tenv terraform install 1.15.6

# Install terraform-docs
TERRAFORM_DOCS_URL="https://terraform-docs.io/dl/v0.24.0/terraform-docs-v0.24.0-linux-amd64.tar.gz"
curl -sSLo ./terraform-docs.tar.gz "$TERRAFORM_DOCS_URL"
tar -xzf terraform-docs.tar.gz
chmod +x terraform-docs
sudo mv terraform-docs /usr/local/bin/terraform-docs
rm -f terraform-docs.tar.gz

# Install pre-commit (non-fatal if not yet available)
if command -v pre-commit &>/dev/null; then
  pre-commit install --hook-type pre-commit --hook-type commit-msg --install-hooks
else
  echo "[WARN] pre-commit not found, skipping hook installation"
fi

echo "Done"
