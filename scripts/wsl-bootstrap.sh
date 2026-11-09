#!/usr/bin/env bash
# One-time setup of the Ansible control node inside WSL (Ubuntu).
# Needs no sudo: everything goes into ~/.local (see DECISIONS.md D-020).
#
#   bash scripts/wsl-bootstrap.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_BIN="$HOME/.local/bin"
ANSIBLE_CORE_VERSION="${ANSIBLE_CORE_VERSION:-2.18.20}"
KUBERNETES_PY_VERSION="${KUBERNETES_PY_VERSION:-37.0.2}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

mkdir -p "$LOCAL_BIN"
export PATH="$LOCAL_BIN:$PATH"

echo "==> Checking Docker (Docker Desktop WSL integration must be on)"
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: 'docker info' failed. Start Docker Desktop and enable"
  echo "       Settings > Resources > WSL Integration > Ubuntu."
  exit 1
fi

echo "==> Installing uv (Python tool installer) into $LOCAL_BIN"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
fi
uv --version

echo "==> Installing ansible-core $ANSIBLE_CORE_VERSION (+ kubernetes client) with Python $PYTHON_VERSION"
uv tool install --force --python "$PYTHON_VERSION" \
  "ansible-core==$ANSIBLE_CORE_VERSION" \
  --with "kubernetes==$KUBERNETES_PY_VERSION" --with "PyYAML" --with "jsonpatch"
ansible --version | head -1

echo "==> Installing Ansible collections"
ANSIBLE_CONFIG="$REPO_DIR/ansible/ansible.cfg" \
  ansible-galaxy collection install -r "$REPO_DIR/ansible/requirements.yml"

echo
echo "Tip: to use kubectl/minikube/helm directly in your shell, add this to ~/.bashrc:"
# shellcheck disable=SC2016  # printed literally on purpose
echo '  export PATH="$HOME/.local/bin:$PATH"'
echo
echo "Bootstrap done. Next:  bash scripts/run-playbook.sh site.yml"
