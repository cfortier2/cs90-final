#!/bin/bash

# this is just a convenience wrapper script to run all of the install scripts

_SCRIPTS="
install_docker.sh
install_haproxy.sh
install_consul.sh
install_pip_requirements.sh
"

for SCRIPT in $_SCRIPTS
do
   /bin/bash $SCRIPT
done
