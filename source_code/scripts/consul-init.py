#
# script attempts to determine the other Consul server peer masters
# based on the current region and availability zone
#
# This is written to be as minimal as possible and only uses built in
# Python libraries to avoid having to install anything :)
#
# this will print the correct join and bootstrap command for Consul
import argparse
import datetime
import os
import signal
import socket
import string
import subprocess
import time
import urllib2

def debug(msg):
    """Print the message if in debug mode"""
    debug = False
    if debug:
        print msg

def get_peer_zones(region, az, domain):
    """Return list of availabilty zones excluding the current one"""
    # iterate through the first 10 characters looking for availability zones
    _zones = []
    for char in string.ascii_lowercase[0:10]:
        # append the char to the region
        test_zone = region + char + domain
        debug(test_zone)

        # do a lookup
        lookup = socket.getfqdn(test_zone)
        debug('lookup: ' + str(lookup))

        if lookup == test_zone:
            debug('not found')
        else:
            # found a valid fqdn
            if test_zone != az + domain:
                _zones.append(test_zone)

    return _zones

def get_az():
    """Return the current availabilty zone"""
    metadata = 'http://169.254.169.254/latest/meta-data'

    # get the availability zone and determine the region
    az = urllib2.urlopen(metadata + '/placement/availability-zone').read()
    return az

def get_region():
    """Return the current region"""
    az = get_az()
    region = az[:-1]
    return region

def run_command(config):
    """Return a list of strings for the subprocess.Popen"""

    # add data-directory
    data_dir_arg = '-data-dir=' + str(config['data_dir'])

    # build bootstrap-expect
    bootstrap_expect_arg = '-bootstrap-expect=' + str(len(config['peer_zones']) + 1)

    # add data center
    dc_arg = '-dc=' + str(config['region'])

    command = ["nohup", "consul", "agent", "-server", data_dir_arg, bootstrap_expect_arg, dc_arg]
    return command

def join_command(config):
    """Return a list of strings to join a consul cluster"""
    join = ['join']
    for zone in config['peer_zones']:
        join += [zone]
    return join

def join_cluster(config):
    """Join a cluster"""
    join_cmd = join_command(config)
    print join_cmd

    # try for a set number of minutes to connect
    connected = False
    attempt_time = 5 # minutes
    start_time = datetime.datetime.now()

    while not connected:
        if datetime.datetime.now() <= start_time + datetime.timedelta(minutes = attempt_time):
            try:
                run_args = ["consul"] + join_command(config)
                consul_process = subprocess.Popen(run_args)
                subpid = consul_process.pid
                consul_process.wait()
                if consul_process.returncode == 0:
                    connected = True
            except KeyboardInterrupt:
                exit("ERROR: Keyboard Interrupt")
            except Exception, e:
                print e
        else:
            exit("ERROR: could not connect to cluster")

    return True

def start_agent(config):
    """Run the consul agent"""
    # check for the pid file and process.
    if get_pid(config['pid_file']):
        if is_running(get_pid(config['pid_file'])):
            print "Consul agent is already running"
            return True
        else:
            print "Consul pidfile exists but the process is not running. Proceed with caution."
            os.remove(config['pid_file'])

    # attempt to start the process
    try:
        print "Attempting to start Consul Agent"
        run_cmd = run_command(config)
        print(run_cmd)
        consul_process = subprocess.Popen(run_cmd)
        subpid = consul_process.pid
        consul_process.poll()
    except Exception, e:
        exit(e)

    # check that it is running
    success = False
    attempt = 0
    max_attempts = 5
    while not success:
        if is_running(subpid):
            write_pidfile(config['pid_file'], subpid)
            print "Consul started successfully"
            success = True
        else:
            if attempt <= max_attempts:
                time.sleep(1)
                attempt += 1
            else:
                exit('Consul did not start')



def get_pid(pid_file):
    """Return the pid of the running process"""
    if os.path.exists(pid_file):
        f = open(pid_file, 'r')
        pid = int(f.read())
        f.close()
        return pid
    else:
        return False

def write_pidfile(pid_file, pid):
    """Write a pid file"""
    try:
        f = open(pid_file, 'w')
        f.write(str(pid))
        f.close()
        return True
    except Exception, e:
        exit(e)

def is_running(pid):
    """Check if the pid is running"""
    try:
        os.kill(pid, 0)
        return True
    except OSError, e:
        return False

def stop_agent(config):
    """Stop the Consul Agent"""
    pid = get_pid(config['pid_file'])
    if pid:
        if is_running(pid):
            os.kill(int(pid), signal.SIGTERM)
            print "Stopping Consul Agent"
        else:
            print "Consul Agent was not running"

        # remove pidfile
        os.remove(config['pid_file'])
        return True
    else:
        print "Consul Agent was not running"

def restart_agent(config):
    """Restart the agent"""
    stop_agent(config)
    start_agent(config)

if __name__ == '__main__':
    # deal with command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='command to run')
    parser.add_argument('--join', help='join a cluster', action = 'store_true')
    args = parser.parse_args()

    config = {
            'data_dir'  : '/opt/consul',
            'domain'    : '.consul',
            'pid_file'  : '/var/run/consul.pid'
            }
    config['peer_zones'] = get_peer_zones(get_region(), get_az(), config['domain'])
    config['region'] = get_region()

    debug(config)

    if args.command == 'start':
        start_agent(config)
        if args.join:
            print "Attempting to join cluster"
            join_cluster(config)
    elif args.command == 'stop':
        stop_agent(config)
    elif args.command == 'restart':
        restart_agent(config)
    else:
        exit(parser.print_help())
