#!/usr/bin/env bash

set -eo pipefail
export LC_ALL=C
unset CDPATH

error() {
    echo >&2 "Error: $*"
}

fatal() {
    error "$@"
    exit 1
}

message() {
    echo >&2 "* $*"
}

if [[ -z "$1" ]]; then
    fatal "No venv directory specified"
fi

VENV_DIR=$1

PY=
PY_VERSION=

replacepath() {
    # [-v var] assign the output to shell variable VAR rather than
    #          display it on the standard output
    # $1 paths separated by ':'
    # $2 path to replace
    # $3 new path
    local var paths npaths oldPath newPath sIFS p
    if [[ "$1" = -v ]]; then
        var=$2
        shift 2
    fi
    paths=$1
    oldPath=$2
    newPath=$3
    sIFS=$IFS
    IFS=":"
    npaths=""
    for p in $paths; do
        if [[ "$p" = "$oldPath" ]]; then
            if [[ -n "$newPath" ]]; then
                if [[ -z "$npaths" ]]; then
                    npaths=$newPath
                else
                    npaths="$npaths:$newPath"
                fi
            fi
        else
            if [[ -z "$npaths" ]]; then
                npaths=$p
            else
                npaths="$npaths:$p"
            fi
        fi
    done
    IFS=$sIFS
    if [[ -n "$var" ]]; then
        printf -v "$var" "%s" "$npaths"
    else
        printf "%s" "$npaths"
    fi
}

init-python-3() {
    local i py py_version
    unset PY PY_VERSION

    # Try to disable existing virtual environment
    message "PATH=$PATH"
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        if [[ -n "${PYTHONHOME:-}" ]]; then
            unset PYTHONHOME
        fi
        replacepath -v PATH "$PATH" "${VIRTUAL_ENV}/bin" ""
        message "PATH=$PATH"
        # Run hash command to forget past commands.  Without forgetting
        # past commands the $PATH changes we made may not be respected
        hash -r
    fi

    # Detect python excutable
    for i in python3 python; do
        if command -v "$i" &>/dev/null; then
            py=$(command -v "$i")
            py_version=$("$py" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
            case "$py_version" in
                3.*)
                    PY=$py
                    # shellcheck disable=SC2034
                    PY_VERSION=$py_version
                    break;;
            esac
        fi
    done

    if [[ -n "$PY" ]]; then
        message "Use python: $PY"
        return 0
    else
        error "No Python 3.x found"
        return 1
    fi
}

init-python-3

if [[ ! -e "$VENV_DIR/bin/activate" ]]; then
    VENV_PARENT_DIR=$(dirname -- "$VENV_DIR")
    VENV_BN=$(basename -- "$VENV_DIR")
    mkdir -p "$VENV_PARENT_DIR"
    pushd "$VENV_PARENT_DIR"
    "$PY" -m venv "$VENV_BN"
    popd
    # shellcheck disable=SC1090
    . "$VENV_DIR/bin/activate"
    # Here python3 refers to the python in the virtual environment
    python3 -m pip install --upgrade pip
    deactivate
fi
