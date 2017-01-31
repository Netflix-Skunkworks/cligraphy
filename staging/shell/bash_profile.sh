export CLIGRAPHY_PYTHON_ENV_ROOT=~/.cligraphy/python-envs

export WORKON_HOME=${CLIGRAPHY_PYTHON_ENV_ROOT}

source ${CLIGRAPHY_PYTHON_ENV_ROOT}/oc/bin/activate

# enable virtualenvwrapper if it's installed
if test -f ${VIRTUAL_ENV}/bin/virtualenvwrapper.sh; then
    source ${VIRTUAL_ENV}/bin/virtualenvwrapper.sh
fi

#
# Handy functions
#

function asn {
  dig +short $(echo $1 | awk -F. '{ print $4"."$3"."$2"."$1".origin.asn.cymru.com" }') TXT
}

function hr {
  for i in $(seq 1 $(tput cols)); do
    echo -n '='
  done
  echo
}

#
# Handy oc shortcuts
#

# We explicitely alias oc to the full path in our virtualenv so that 'oc' commands work when we're working in another virtualenv,
# and we alias to python -m as the default wrapper adds 0.1s
alias oc='${CLIGRAPHY_PYTHON_ENV_ROOT}/oc/bin/python -m cligraphy.core.cli'
alias repos='oc dev repos'
alias lint='oc dev lint'
alias tests='oc dev tests'
alias rebash='source ~/.bash_profile; hash -r'

#
# Handy aliases
#

alias json="python -c 'import json; import sys; print json.dumps(json.load(open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin), indent=4)'"
alias rpurge='find . -name *~ -exec rm -i {} \;'

#
# oc command completion
#

source ${CLIGRAPHY_REPO_PATH}/shell/bash_complete.sh

#
# Shellshock reporting - probably want to remove this some time in 2015
#

env x='() { :;}; echo WARNING - Your shell is vulnerable to shellshock - http://go/shellshock' bash -c "echo -n"
