#!/bin/bash

_DOWNLOADS="
0.4.1_linux_amd64.zip
0.4.1_web_ui.zip
"

_DL_URL='https://dl.bintray.com/mitchellh/consul'

apt-get update && apt-get install unzip -y

mkdir -p /opt/consul

cd /opt/consul

for FILE in $_DOWNLOADS
do
  wget $_DL_URL/$FILE
  unzip $FILE
done

ln -s /opt/consul/consul /usr/local/bin/
