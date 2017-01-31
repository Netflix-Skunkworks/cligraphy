# OC Setup - Common bash shell library

function oc_log {
  #logger -t "$@"
  echo "$@" >>${CLIGRAPHY_LOG-/dev/null}
}

function oc_debug {
  if test ${CLIGRAPHY_DEBUG-0} -eq 1; then
    oc_log "${CLIGRAPHY_SETUP_APP-setup} [DEBUG] $@"
  fi
}

function oc_info {
  oc_log "${CLIGRAPHY_SETUP_APP-setup} [INFO ] $@"
}

function oc_warn {
  oc_log "${CLIGRAPHY_SETUP_APP-setup} [WARN ] $@"
}

function oc_err {
  oc_log "${CLIGRAPHY_SETUP_APP-setup} [ERR  ] $@"
  oc_failure
}

function oc_no_root {
  if test $UID -eq 0; then
    oc_err "Do not run this script as root!"
  fi
}

function oc_success {
  CLIGRAPHY_SUCCESS=1
  exit 0
}

function oc_failure {
  CLIGRAPHY_SUCCESS=0
  exit 1
}

# Strict (and default) shell error checking:
# - exit on command failures
# - treat unbound variables as errors (use ${missing-default} !)
function oc_strict {
  set -e
  set -u
}

# Function args checking
function oc_args {
  if test $1 -ne $2; then
    oc_err "Wrong argument count, expected $1, got $2"
    exit 1
  fi
}

function oc_capture {
  oc_debug "oc_capture: [$@] --- output follows ---"
  out=$("$@" 2>&1)
  oc_debug "${out}"
  oc_debug "oc_capture: --- end of output ---"
  echo "$out"
}


function oc_capture_ignore_fail {
  oc_debug "oc_capture: [$@] --- output follows ---"
  set +e
  out=$("$@" 2>&1)
  set -e
  oc_debug "${out}"
  oc_debug "oc_capture: --- end of output ---"
  echo "$out"
}


# Run a command, capturing output in our log
function oc_run {
  oc_debug "oc_run: [$@] --- output follows ---"

  set +e
  "$@" 1>>${CLIGRAPHY_LOG-/dev/null} 2>&1
  declare -r ret=${?}
  set -e

  oc_debug "oc_run: --- end of output ---"

  if test ${ret} -ne 0; then
    oc_warn "Command failed with exit code ${ret}"
    exit ${ret}
  fi
}

function oc_run_ignore_fail {
  oc_debug "oc_run: [$@] --- output follows ---"

  set +e
  "$@" 1>>${CLIGRAPHY_LOG-/dev/null} 2>&1
  declare -r ret=${?}
  set -e

  oc_debug "oc_run: --- end of output ---"
}

# Run a command as root, capturing output in our log
function oc_sudo {
  c="$@"
  oc_run sudo -p "sudo[$c'] password: " "$@"
}
