#!/bin/bash

_CONSUL_ZIP=0.4.1_linux_amd64.zip

apt-get update && apt-get install unzip -y

mkdir -p /opt/consul

cd /opt/consul
wget https://dl.bintray.com/mitchellh/consul/$_CONSUL_ZIP

unzip $_CONSUL_ZIP

ln -s /opt/consul/consul /usr/local/bin/
