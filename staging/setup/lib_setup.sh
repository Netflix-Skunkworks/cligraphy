# OC Setup library

source ${CLIGRAPHY_REPO_PATH}/shell/lib.sh

function oc_setup_init {
  if test -z "${CLIGRAPHY_LOG-}"; then
    # NB: these XXXXX are here for compat with ubuntu's mktemp
    CLIGRAPHY_LOG=$(mktemp -t ocsetup-log-${app}-XXXXXX)
  fi

  trap oc_setup_cleanup EXIT
}

function oc_setup_cleanup {
  code=${?}
  if test ${code} -ne 0; then
    echo "Exiting with status ${code}"
    echo "--- execution log ---"
    cat ${CLIGRAPHY_LOG}
    echo "--- end execution log ---"
  fi
}

function oc_setup_init_app {

  oc_setup_init
  oc_strict

  oc_args $# 1
  declare -r app=$1

  # general
  # NB: these XXXXX are here for compat with ubuntu's mktemp
  CLIGRAPHY_TMP=$(mktemp -d -t ocsetup-${app}-XXXXXX)
  CLIGRAPHY_PREV_PWD=${PWD}
  cd ${CLIGRAPHY_TMP}

  # setup-app specific
  CLIGRAPHY_SETUP_APP=${app}
  CLIGRAPHY_SETUP_APP_PATH=${CLIGRAPHY_REPO_PATH}/setup/${CLIGRAPHY_SETUP_APP}

  # trap
  CLIGRAPHY_CLEANUP_HOOKS[0]="true"
  trap 'oc_setup_cleanup_app ${LINENO}' EXIT

  oc_debug init done
}

function oc_add_cleanup_hook {
  index=${#CLIGRAPHY_CLEANUP_HOOKS[@]}
  eval CLIGRAPHY_CLEANUP_HOOKS[${index}]='"$@"'
}

function oc_setup_cleanup_app {

  code=${?}
  line=${1}

  oc_debug "exit trap called from line ${1}, code ${code}"

  for ((i = 0; i < ${#CLIGRAPHY_CLEANUP_HOOKS[@]}; i++)); do
    ${CLIGRAPHY_CLEANUP_HOOKS[$i]}
  done

  cd ${CLIGRAPHY_PREV_PWD}
  rm -rf ${CLIGRAPHY_TMP}

  oc_debug cleanup done

  if test ${CLIGRAPHY_SUCCESS-0} -ne 1; then
    exit 1
  fi
}
