#!/bin/bash

# deploy b
# this only needs to be run on ONE of the consul servers
#

curl -X PUT -d 'cfortier/cs90:b' http://localhost:8500/v1/kv/cs90/active/image
curl -X PUT -d '82' http://localhost:8500/v1/kv/cs90/active/port
curl -X PUT -d 'server82' http://localhost:8500/v1/kv/cs90/active/enableserver
curl -X PUT -d 'server81' http://localhost:8500/v1/kv/cs90/active/disableserver
