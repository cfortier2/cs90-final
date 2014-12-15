# this is a preliminary script to deploy a running docker container

# random notes:
#
# for this initial phase, we will only run a maximum of two application
# containers at a time on ports 81 and 82
#

# steps:
# [] install haproxy TODO: move this to chef
# [] install docker TODO: move this to chef
# [] query key/value store for /prosite/active/image which should return a `repo/image:tag` value
# [] query key/value store for /prosite/active/port which should return a `port` value
# [] query key/value store for /prosite/active/enableserver which should return a `name` value
# [] query key/value store for /prosite/active/disableserver which should return a `name` value
# [] check if current version is running.
#      if true, run health check
#      else:  pull container, run container, update haproxy, health check
#

import argparse
import consul
import docker
import json
import os
import urllib2
import sys
import time

def get_active(consul, product):
    """Return a dict containing all tags under 'product/active' from Consul."""

    # build the active key path
    key = product + '/active/'
    return get_key(consul, key)

def get_key(consul, key):
    index, data = consul.kv.get(key, recurse = True)

    if data:
        # create a dict that only contains the key name (without parent directory)
        # and value such as: {u'image': 'cfortier/phpinfo:latest', u'port': '81'}
        result = {k['Key'].split('/')[-1]: k['Value'] for k in data if k['Value'] != None}
        return result
    else:
        return False

def get_running_containers(docker):
    """Return list of container objects for running containers"""
    containers = docker.containers()
    print "running containers:"
    for container in containers:
        print "  ", container['Image']
    return containers

def get_stage(consul, product):
    """Return a dict containing all tags under 'product/stage' from Consul."""

    # build the stage key path
    key = product + '/stage/'
    return get_key(consul, key)

def haproxy_status():
    # TODO: implement this better
    status = os.system('service haproxy status')
    if status == 0:
        return True
    else:
        return False

def health_check(address, sleep = 2):
    """Curl the address and check for a 200"""
    # need to sleep a bit for the container to start
    time.sleep(sleep)

    print "Checking health of: " + str(address)

    # this is prone to erroring out
    # TODO: implement a retry
    try:
        health_check = urllib2.urlopen(address)
        if health_check.code == 200:
            print "Health check success"
            return True
        else:
            return False
    except urllib2.URLError as e:
        print "ERROR: health_check encountered an error checking: " + str(address)

def is_container_running(docker_client, image):
    """Return boolean if image is currently running"""
    # get the running containers
    running_containers = get_running_containers(docker_client)
    return image in [container['Image'] for container in running_containers]

# def pull_container(client, image):
#     """Pull the requested image to client"""
#     return True

def run_container(docker_client, image, port):
    """Run the requested image"""

    # check if active container is running
    if is_container_running(docker_client, image):
        print "Container:", image, "is already running"
    else:
        print "Container:", image, "is NOT running"

        # get container
        print "Pulling image", image
        for line in docker_client.pull(image, stream = True):
            print(json.dumps(json.loads(line), indent = 4))

        # run container
        # TODO: add run_command to k/v store
        # the python library requires a create then start model
        print "creating container"
        container = docker_client.create_container(image = image)
        print "created container:", container

        print "starting container"
        time.sleep(1)
        start_response = docker_client.start(container = container.get('Id'), port_bindings={80:port})

        # health check
        if health_check('http://127.0.0.1:' + port):
            return True
        else:
            sys.exit('ERROR: Container failed health check')

def run_init(docker_client, consul_client, product):
    """Run the requested image.
        Assumptions are made that this is the initial launch on an instance."""

    print "***** Initializing *****"
    # get the active key from Consul
    config = get_active(consul_client, product)
    container_started = run_container(docker_client, config['image'], config['port'])

    # ha proxy
    if container_started:
        set_haproxy(config['enableserver'], config['disableserver'])

def set_haproxy(enable, disable):
    """Enable a server and disable the other"""
    # NOTE: this needs to be seriously refactored to allow for an arbitrary
    # list of servers.

    # make sure HA Proxy is running
    if not haproxy_status():
        start = start_haproxy()

    # update config
    enable_command = 'echo "enable server app/' + enable + '" | socat stdio /etc/haproxy/haproxysock'
    disable_command = 'echo "disable server app/' + disable + '" | socat stdio /etc/haproxy/haproxysock'

    enabled = os.system(enable_command)
    disabled = os.system(disable_command)

    return True

def start_haproxy():
    if not haproxy_status():
        start = os.system('service haproxy start')
        if start == 0:
            return True
        else:
            os.exit("ERROR: Could not start HA Proxy")
    else:
        return True

def daemon(docker_client, consul_client, product):
    """Daemon mode to constantly poll for changes in Consul"""
    """ NOTE this may not be the most fault tolerant of ways to handle this.
    This will poll for a change in the `stage` tag and start a blocking
    transaction until it is ready to deploy as the active. Ideally we will
    need to make this several independent steps that can be recovered after
    a crash"""

    print "***** Starting daemon mode *****"
    # loop forever
    while True:
        print 'daemon poll'
        time.sleep(1)

        # this is what consul is telling us should be happening
        active = get_active(consul_client, product)
        stage = get_stage(consul_client, product)

        # on an initial bootstrap, `stage` may not be set
        if stage == False:
            continue

        # if the stage container is not running. Start it, but DO NOT update
        # HA proxy yet. If the stage container is NOT running, it SHOULD
        # mean that a new deployment is occuring. But this isn't fully
        # fleshed out yet.

        if active['image'] != stage['image']:
            print "active['image']:", active['image'], "stage['image']:", stage['image'], " == difference detected"
            active_transaction = True

            if not is_container_running(docker_client, stage['image']):
                print "stage container is not running"
                run_container(docker_client, stage['image'], stage['port'])

            # we will wait until the stage image is "promoted" to active.
            # check to see if the active container has changed
            while active_transaction:
                active = get_active(consul_client, product)
                print "waiting to deploy new container"
                print 'active', active['image']
                print 'stage', stage['image']
                if active['image'] == stage['image']:
                    # then its safe to "promote" the stage container and set
                    # the active container to maintenance mode
                    print "DEPLOYING:", active['image']
                    set_haproxy(enable = active['enableserver'], disable = active['disableserver'])
                    active_transaction = False

                    # print "sleeping for 30 seconds for the demo"
                    # time.sleep(30)
                    # stop old container?

                else:
                    time.sleep(1)
        else:
            print "active['image']:", active['image'], "stage['image']:", stage['image'], " == same"



if __name__ == '__main__':
    consul_host = '127.0.0.1'
    docker_host = 'unix://var/run/docker.sock'

    product = 'cs90'

    # deal with command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', help='used for initial launch', action='store_true')
    parser.add_argument('--daemon', help='daemon mode', action='store_true')
    args = parser.parse_args()

    # gather clients
    consul_client = consul.Consul(host = consul_host)
    docker_client = docker.Client(docker_host)

    # run based on command line args
    if args.init:
        run_init(docker_client, consul_client, product)
    elif args.daemon:
        run_init(docker_client, consul_client, product)
        daemon(docker_client, consul_client, product)
    else:
        print "ERROR: you did not specify any commands"

