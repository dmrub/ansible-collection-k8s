#!/usr/bin/env bash

set -eo pipefail

THIS_DIR=$( cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P )

# shellcheck source=init-env.sh
source "$THIS_DIR/init-env.sh"

#if [[ -e "$KUBESPRAY_DIR/disable-firewall.yml" ]]; then
#    run-ansible-playbook "$KUBESPRAY_DIR/disable-firewall.yml" "$@"
#fi
#
#if [[ -e "$KUBESPRAY_DIR/disable-swap.yml" ]]; then
#    run-ansible-playbook "$KUBESPRAY_DIR/disable-swap.yml" "$@"
#fi

run-ansible-playbook "$THIS_DIR/../playbooks/disable-firewall.yml" "$@"

run-ansible-playbook "$THIS_DIR/../playbooks/disable-swap.yml" "$@"

run-ansible all -m setup

run-ansible-playbook "$KUBESPRAY_DIR/cluster.yml" --become --become-user=root "$@"
