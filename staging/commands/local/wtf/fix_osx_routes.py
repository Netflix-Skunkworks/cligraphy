#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""
Fix bogus routes left by Juniper Network Connect on OSX
"""

import tempfile
import os


def exec_bash_code(code):
    with tempfile.NamedTemporaryFile() as tmpfp:
        tmpfp.write(code)
        tmpfp.flush()
        os.system('/bin/bash %s' % tmpfp.name)


def main():
    exec_bash_code("""#!/usr/bin/env bash
IFS='
'
interfaces=$(networksetup -listnetworkserviceorder | grep -E '\(\d+|\*\)' | cut -d' ' -f2- | grep -iE 'ethernet|wi-fi|iPhone')

enabled=()
echo "Listing enabled interfaces"
for i in ${interfaces}; do
    if test $(networksetup -getnetworkserviceenabled "${i}") = 'Enabled'; then
        echo "  ${i}"
        enabled+=(${i})
    else
        enabled+=(${i})
    fi
done

echo
echo "Will use sudo to disable and re-enable interfaces listed above."
echo
echo "Continue? (enter, or ctrl-c to abort)"
read junk

echo "Disabling..."
for i in ${enabled[@]}; do
    sudo networksetup -setnetworkserviceenabled ${i} off
done

echo "Done disabling, sleeping 2s..."
sleep 2

echo "Re-enabling..."
for i in ${enabled[@]}; do
    sudo networksetup -setnetworkserviceenabled ${i} on
done
""")
