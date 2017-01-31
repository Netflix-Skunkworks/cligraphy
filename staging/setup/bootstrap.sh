#!/usr/bin/env bash
# octools bootstrap
# curl -L go/octools.sh | bash


function exit_trap {
    cat <<\EOF
------------------------------------------------------------------------------

      ▄██████████████▄▐█▄▄▄▄█▌
      ██████▌▄▌▄▐▐▌███▌▀▀██▀▀  octools bootstrap script exited unexpectedly
      ████▄█▌▄▌▄▐▐▌▀███▄▄█▌
      ▄▄▄▄▄██████████████▀

------------------------------------------------------------------------------
EOF
}

trap exit_trap EXIT

# resize terminal to 42x100
printf '\e[8;42;100t'
clear

cat <<\EOF
------------------------------------------------------------------------------

      ██████╗  ██████╗████████╗ ██████╗  ██████╗ ██╗     ███████╗
     ██╔═══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██╔════╝
     ██║   ██║██║        ██║   ██║   ██║██║   ██║██║     ███████╗
     ██║   ██║██║        ██║   ██║   ██║██║   ██║██║     ╚════██║
     ╚██████╔╝╚██████╗   ██║   ╚██████╔╝╚██████╔╝███████╗███████║
      ╚═════╝  ╚═════╝   ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚══════╝

 ██████╗  ██████╗  ██████╗ ████████╗███████╗████████╗██████╗  █████╗ ██████╗
 ██╔══██╗██╔═══██╗██╔═══██╗╚══██╔══╝██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗
 ██████╔╝██║   ██║██║   ██║   ██║   ███████╗   ██║   ██████╔╝███████║██████╔╝
 ██╔══██╗██║   ██║██║   ██║   ██║   ╚════██║   ██║   ██╔══██╗██╔══██║██╔═══╝
 ██████╔╝╚██████╔╝╚██████╔╝   ██║   ███████║   ██║   ██║  ██║██║  ██║██║
 ╚═════╝  ╚═════╝  ╚═════╝    ╚═╝   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝

------------------------------------------------------------------------------

This script is intended to run on fresh new computers. It will install a basic
set of dependencies and configure octools.

------------------------------------------------------------------------------

Hit enter to continue, or CTRL-C
EOF

read junk </dev/tty

echo "Checking platform..."
platform=$(uname)
if test ${platform} != "Darwin"; then
    echo "Sorry, this script is OSX specific. Please install octools manually (see README.md)"
    exit 1
fi

OSX_VERS=$(sw_vers -productVersion | cut -d. -f2)
if [ "$OSX_VERS" -lt 11 ]; then
    echo "Sorry, this version of OSX is too damn old."
    echo "Please upgrade to 10.11 (El Capitan)"
    exit 1
fi

echo "Checking that sudo works..."
set -e
sudo touch /tmp/sudo.works
set +e

echo "Checking for xcode command line tools..."
if ! pkgutil --pkg-info=com.apple.pkg.CLTools_Executables; then
    echo "Installing xcode command line tools..."
    touch /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
    xcodeproduct=$(softwareupdate -l | grep "\*.*Command Line" | head -n 1 | awk -F"*" '{print $2}' | sed -e 's/^ *//' | tr -d '\n')
    sudo softwareupdate -i "${xcodeproduct}" -v
    rm /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress

    if ! pkgutil --pkg-info=com.apple.pkg.CLTools_Executables; then
        echo "Failed to install the xcode command line tools with softwareupdate"
        echo "Trying another approach... A dialog should appear: just click 'Install'"
        echo "Once done, please re-run this script."
        xcode-select --install
        exit 1
    fi
fi


set -e


REPO_PATH=${REPO_PATH:-~/repos}

echo "Cloning octools git repo to ${REPO_PATH}/octools ..."

# checkout or update octools
if test -d ${REPO_PATH}/octools; then
    cd ${REPO_PATH}/octools
    git pull
else
    mkdir -p ${REPO_PATH}

    # OPENSOURCE TODO
    git clone https://git.domain.net/cligraphy-core.git ${REPO_PATH}/cligraphy-core

    cd ${REPO_PATH}/octools
fi

echo "Creating base octools directories..."
mkdir -p ~/.cligraphy
mkdir -p ~/.cligraphy/backup
mkdir -p ~/.cligraphy/python-envs
mkdir -p ~/.cligraphy/run

BREW=/usr/local/bin/brew

echo "Checking for homebrew..."
if ! test -f $BREW ; then
    echo "Installing homebrew..."
    ruby ${REPO_PATH}/cligraphy-core/setup/homebrew/install.rb
    # re-read paths after installing homebrew
    eval `/usr/libexec/path_helper -s`
fi

echo "Updating homebrew..."
$BREW update

# start bootstrapin'
if test -d /tmp/oc-bootstrap; then
    rm -rf /tmp/oc-bootstrap
fi
mkdir /tmp/oc-bootstrap
cd /tmp/oc-bootstrap

echo "Installing python from homebrew..."
if ! test -f /usr/local/bin/python; then
    $BREW install python
fi

/usr/local/bin/pip install -U pip setuptools wheel PyYAML
/usr/local/bin/pip install -I virtualenv


echo "Installing our dependencies from homebrew..."
$BREW list -1 >/tmp/oc-bootstrap/brew.installed
/usr/local/bin/python ${REPO_PATH}/cligraphy-core/setup/packages.py ${REPO_PATH}/cligraphy-core/setup/packages.yaml >/tmp/oc-bootstrap/brew.wanted
/usr/local/bin/python ${REPO_PATH}/cligraphy-core/setup/missing.py /tmp/oc-bootstrap/brew.installed /tmp/oc-bootstrap/brew.wanted /tmp/oc-bootstrap/brew.missing
if test -f /tmp/oc-bootstrap/brew.missing; then
    cat /tmp/oc-bootstrap/brew.missing | xargs $BREW install
fi

echo "Creating our octools venv..."

# switch to octools
if test -d ~/.cligraphy/python-envs/oc; then
    rm -rf ~/.cligraphy/python-envs/oc
fi

/usr/local/bin/virtualenv ~/.cligraphy/python-envs/oc
source ~/.cligraphy/python-envs/oc/bin/activate

pip install -U pip setuptools wheel

# make sure pip builds against brew-installed headers and libs, gmp and ssl in particular
export CFLAGS='-I/usr/local/include -L/usr/local/lib -L/usr/local/opt/openssl/lib'

echo "Installing python dependencies in the octools venv..."


# OPENSOURCE TODO

cd ${REPO_PATH}/octools
#pip install --trusted-host pypi.domain.net -i https://pypi.domain.net/pypi/ -r requirements.txt
python setup.py develop --no-deps

echo "Setting up your bash profile..."
export CLIGRAPHY_REPO_PATH=${REPO_PATH}/octools
./setup/setup base

echo "Refreshing commands..."
source ./shell/oc_bash_profile.sh
oc --autodiscover refresh -q


trap EXIT

cat <<\EOF

------------------------------------------------------------------------------

            All done!
            Please start a new terminal session and close this one

------------------------------------------------------------------------------

EOF
