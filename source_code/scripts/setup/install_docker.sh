#!/bin/bash

if [[ $(grep Ubuntu /etc/lsb-release | wc -l) -gt 0 ]]
then
  echo "ubuntu!"
    if [[ $(dpkg -l | grep docker.io | wc -l) -eq 0 ]]
    then
      echo "Docker is not installed, installing now"
      apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9
      sh -c "echo deb https://get.docker.com/ubuntu docker main > /etc/apt/sources.list.d/docker.list"
      apt-get update
      # apt-get install docker.io -y
      apt-get install lxc-docker -y
      source /etc/bash_completion.d/docker.io
    else
      echo "Docker is already installed, skipping"
    fi
fi
