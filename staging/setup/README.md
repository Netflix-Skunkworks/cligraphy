oc/setup - Set up and maintain your environment
===============================================

This module takes care of bootstraping the oc toolset, and of maintaining up to date.

Basic structure
---------------

In base/, we create our base directory structure ($HOME/oc) and make sure your bash profile has the bits necessary for oc tools to work.

Native packages: Homebrew / Apt / Yum
--------------------------------------

On OSX, we use homebrew to install most native packages.
We run homebrew from a private fork tn order to control and manage versioning.

On other systems, non-python packages are installed by the package manager.

The list of packages we install is in packages.yaml

Python
------

Installs a recent pip in the system path if that's missing.

Also creates a virtualenv for oc tools and install the tools (and their dependencies).
