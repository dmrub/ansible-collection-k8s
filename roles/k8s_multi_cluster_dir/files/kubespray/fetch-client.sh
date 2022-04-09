#!/usr/bin/env bash

THIS_DIR=$( cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P )

# shellcheck source=init-env.sh
source "$THIS_DIR/init-env.sh"

set -e

run-ansible all -m setup

PLAYBOOKS=("$KUBESPRAY_DIR/fetch-client.yml" "$THIS_DIR/../playbooks/fetch-client.yml")

for FN in "${PLAYBOOKS[@]}"; do
    if [[ -e "$FN" ]]; then
        PLAYBOOK=$FN
        break
    fi
done

if [[ -n "$PLAYBOOK" ]]; then
    run-ansible-playbook "$PLAYBOOK" "$@"
else
    fatal "Found no playbook: ${PLAYBOOKS[*]}"
fi
