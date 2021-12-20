#!/usr/bin/env bash

THIS_DIR=$( cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P )

# shellcheck source=init-env.sh
source "$THIS_DIR/init-env.sh"

set -e

run-ansible all -m setup

PLAYBOOK=$THIS_DIR/../playbooks/fetch-client.yml

if [[ -e "$PLAYBOOK" ]]; then
    run-ansible-playbook "$PLAYBOOK" "$@"
else
    fatal "No playbook $PLAYBOOK"
fi
