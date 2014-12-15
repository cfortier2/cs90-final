#!/bin/bash
_LIST="
54.174.41.121
54.173.114.64
54.174.243.88
54.175.5.13
54.172.45.65
54.86.83.9
"

for i in $_LIST
do
    rsync -avhP * ubuntu@$i:~/cs90
done
