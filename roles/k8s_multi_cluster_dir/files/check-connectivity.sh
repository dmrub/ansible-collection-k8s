#!/usr/bin/env bash

set -eo pipefail

THIS_DIR=$( cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P )

# shellcheck source=init-env.sh
source "$THIS_DIR/init-env.sh"

if [[ -e "$KUBESPRAY_DIR/create-ssh-scripts.yml" ]]; then
    run-ansible-playbook \
        "$KUBESPRAY_DIR/check-connectivity.yml" \
        "$@"
else
    fatal "No playbook $KUBESPRAY_DIR/check-connectivity.yml"
fi
