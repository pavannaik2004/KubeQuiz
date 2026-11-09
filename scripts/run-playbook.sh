#!/usr/bin/env bash
# Run an Ansible playbook from ansible/ with the repo's config.
#
# The repo lives on a Windows drive (/mnt/d/...), which WSL mounts as
# world-writable, and Ansible refuses to read ansible.cfg from such a
# directory. Pointing ANSIBLE_CONFIG at it explicitly works around that.
#
#   bash scripts/run-playbook.sh site.yml [extra ansible-playbook args]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"
export ANSIBLE_CONFIG="$REPO_DIR/ansible/ansible.cfg"

playbook="${1:-site.yml}"
shift || true

cd "$REPO_DIR/ansible"
exec ansible-playbook "$playbook" "$@"
