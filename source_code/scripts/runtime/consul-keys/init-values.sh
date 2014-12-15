#!/bin/bash

# this is used to populate the inital consul key/value
# this only needs to be run on ONE of the consul servers
#

curl -X PUT -d 'cfortier/cs90:a' http://localhost:8500/v1/kv/cs90/active/image
curl -X PUT -d '81' http://localhost:8500/v1/kv/cs90/active/port
curl -X PUT -d 'server81' http://localhost:8500/v1/kv/cs90/active/enableserver
curl -X PUT -d 'server82' http://localhost:8500/v1/kv/cs90/active/disableserver

curl -X DELETE -d '' http://localhost:8500/v1/kv/cs90/stage/image
curl -X DELETE -d '' http://localhost:8500/v1/kv/cs90/stage/port
curl -X DELETE -d '' http://localhost:8500/v1/kv/cs90/stage/enableserver
curl -X DELETE -d '' http://localhost:8500/v1/kv/cs90/stage/disableserver
