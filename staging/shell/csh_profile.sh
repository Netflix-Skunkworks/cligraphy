setenv CLIGRAPHY_PYTHON_ENV_ROOT ~/.cligraphy/python-envs
setenv PATH ${PATH}:${CLIGRAPHY_REPO_PATH}/bin

source ${CLIGRAPHY_PYTHON_ENV_ROOT}/oc/bin/activate.csh

#
# Handy oc shortcuts
#

# We explicitely alias oc to the full path in our virtualenv so that 'oc' commands work when we're working in another virtualenv,
# and we alias to python -m as the default wrapper adds 0.1s
alias oc '${CLIGRAPHY_PYTHON_ENV_ROOT}/oc/bin/python -m cligraphy.core.cli'
alias repos 'oc dev repos'
alias lint 'oc dev lint'
alias tests 'oc dev tests'

#
# Handy aliases
#

alias json="python -c 'import json; import sys; print json.dumps(json.load(open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin), indent=4)'"
alias rpurge='find . -name *~ -exec rm -i {} \;'
