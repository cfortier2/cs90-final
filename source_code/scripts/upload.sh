#!/bin/bash
_LIST="
54.175.18.27
54.175.10.74
54.174.10.17
54.84.143.62
54.174.239.253
54.175.1.143
"

for i in $_LIST
do
    rsync -avhP * ubuntu@$i:~/cs90
done
