#
# this script is to create Route53 entries for the Consul Servers.
# this can only be run once the private zone has been created.
#
# process:
#   query ec2 looking for instance tags with `consul-server`
#   create dns name
#
import boto
import boto.ec2
import boto.route53

def get_consul_instances(region):
    """Return list of instance objects for all consul instances in this account/region"""

    all_instances = ec2.get_only_instances()

    consul_servers = []

    # filter for only the consul instances
    print "Looking for Consul Server instances..."
    for i in all_instances:
        if i.tags['Name'] == 'consul-server':
            print "  Consul Server:", i
            consul_servers.append(i)

    return consul_servers

# locate the correct zone
def get_zone(name):
    zones = route53.get_zones()
    for zone in zones:
        if zone.name == name:
                return zone

def create_route53_record(fqdn, cname_target, zone_name):
    """Create Route53 CNAME record for a given cname.
        fqdn is the name we wish to create. like consul.us-east-1a.cs90
        cname_target is the private dns name of the instance"""
    zone = get_zone(zone_name)

    # add cname
    if not zone.find_records(fqdn, 'CNAME'):
        print "Creating cname for:", fqdn
        result_host = zone.add_cname(fqdn, cname_target)
    else:
        print "cname already exists for:", fqdn
        result_host = zone.update_cname(fqdn, cname_target)

    return result_host

def create_all(config):
    instances = get_consul_instances(config['region'])

    for instance in instances:
        fqdn = 'consul.' + instance.placement + '.' + config['zone']
        create_route53_record(fqdn, instance.private_dns_name, config['zone'])

if __name__ == '__main__':
    config = {
            'region': 'us-east-1',
            'zone': 'cs90.'
            }

    # create connections for all functions to use
    route53 = boto.connect_route53()
    ec2 = boto.ec2.connect_to_region(config['region'])

    # create the records
    create_all(config)
