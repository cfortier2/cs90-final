#!/usr/bin/python
from troposphere import Ref, Template, Tags, Parameter, UpdatePolicy
from troposphere.autoscaling import AutoScalingGroup
from troposphere.autoscaling import LaunchConfiguration
from troposphere.autoscaling import Tag
from troposphere.ec2 import Instance
from troposphere.ec2 import InternetGateway
from troposphere.ec2 import EBSBlockDevice
from troposphere.ec2 import BlockDeviceMapping
from troposphere.ec2 import Route
from troposphere.ec2 import RouteTable
from troposphere.ec2 import SecurityGroup
from troposphere.ec2 import SecurityGroupIngress
from troposphere.ec2 import Subnet
from troposphere.ec2 import SubnetRouteTableAssociation
from troposphere.ec2 import VPC
from troposphere.ec2 import VPCGatewayAttachment
from troposphere.elasticloadbalancing import LoadBalancer
from troposphere.elasticloadbalancing import Listener

# config things
config = {
        'app_asg': {
            'availability_zones': ['us-east-1a', 'us-east-1b', 'us-east-1d'],
            'instance_name': 'demo-host',
            'max_size': 3,
            'min_size': 3
            },
        'app_launch_config': {
            'block_device': {
                'delete_on_termination': True
                },
            'ebs_optimized': False,
            'image_id': 'ami-9eaa1cf6',
            'instance_type': 't2.medium',
            'key_name': 'fortier'
            },
        'consul_asg': {
            'availability_zones': ['us-east-1a', 'us-east-1b', 'us-east-1d'],
            'instance_name': 'consul-server',
            'max_size': 3,
            'min_size': 3
            },
        'consul_launch_config': {
            'block_device': {
                'delete_on_termination': True
                },
            'ebs_optimized': False,
            'image_id': 'ami-9eaa1cf6',
            'instance_type': 't2.medium',
            'key_name': 'fortier'
            },
        'name': 'demo',
        'region': 'us-east-1',
        'vpc': {
            'app_subnets': [
                ('1', '10.43.1.0/24', 'us-east-1a'),
                ('2', '10.43.2.0/24', 'us-east-1b'),
                ('3', '10.43.3.0/24', 'us-east-1d')
                ],
            'cidr_block': '10.43.1.0/16',
            'name': 'demo'
            }
        }



# the template object
t = Template()

# create VPC
vpc = VPC(config['name'] + 'Vpc')
vpc.CidrBlock = config['vpc']['cidr_block']
vpc.EnableDnsSupport = True
vpc.EnableDnsHostnames = True
vpc.Tags = Tags(Name=config['vpc']['name'])
t.add_resource(vpc)

# internet gateway
internet_gateway = InternetGateway('InternetGateway')
t.add_resource(internet_gateway)

gateway_attachment = VPCGatewayAttachment('GatewayAttachment')
gateway_attachment.VpcId = Ref(vpc)
gateway_attachment.InternetGatewayId = Ref('InternetGateway')
t.add_resource(gateway_attachment)

# route table
route_table = RouteTable(config['name'] + 'RouteTable')
route_table.VpcId = Ref(config['name'] + 'Vpc')
route_table.Tags=Tags(
        Application = Ref('AWS::StackName'),
        Name = config['name'] + '-route-table'
        )
t.add_resource(route_table)

# route to igw
route_igw = Route(config['name'] + 'Igw')
route_igw.DestinationCidrBlock = '0.0.0.0/0'
route_igw.GatewayId = Ref(internet_gateway)
route_igw.RouteTableId = Ref(route_table)
t.add_resource(route_igw)

# subnets
app_subnets = []
route_table_associations = []
for subnet in config['vpc']['app_subnets']:
    sub = Subnet('PublicSubnet' + subnet[0])
    sub.VpcId = Ref(vpc)
    sub.CidrBlock = subnet[1]
    sub.AvailabilityZone = subnet[2]
    sub.Tags = Tags(Application = Ref('AWS::StackName'))
    t.add_resource(sub)
    app_subnets.append(sub)

    # route table associations need to be handled per subnet
    rta = SubnetRouteTableAssociation(config['name'] + 'Rta' + subnet[0])
    rta.RouteTableId = Ref(route_table)
    rta.SubnetId = Ref(sub)
    t.add_resource(rta)
    route_table_associations.append(rta)

# security group addresses
# list of tuples
# [('cidr block', 'cloudformation resource name')]
home_egress_ips = [
    ('68.193.66.133/32', 'home')
        ]

# security groups
home_ssh = SecurityGroup(config['name'] + 'homeSsh')
home_ssh.GroupDescription = 'home SSH in'
home_ssh.VpcId = Ref(vpc)
home_ssh.Tags = Tags(Name = config['name'] + '-home-ssh')
t.add_resource(home_ssh)

consul_sg = SecurityGroup('consul')
consul_sg.GroupDescription = 'consul cluster'
consul_sg.VpcId = Ref(vpc)
consul_sg.Tags = Tags(Name = config['name'] + '-consul')
t.add_resource(consul_sg)

# consul ports
consul_ports = [
        8300,
        8301,
        8302,
        8400,
        8500,
        8600
        ]

for port in consul_ports:
    rule = SecurityGroupIngress('consul' + str(port))
    rule.SourceSecurityGroupId = Ref(consul_sg)
    rule.FromPort = port
    rule.ToPort = port
    rule.GroupId = Ref(consul_sg)
    rule.IpProtocol = 'tcp'
    t.add_resource(rule)

# access web ui from home
consul_ui_rule = SecurityGroupIngress('consulUi')
consul_ui_rule.CidrIp = home_egress_ips[0][0]
consul_ui_rule.FromPort = 8500
consul_ui_rule.ToPort = 8500
consul_ui_rule.GroupId = Ref(consul_sg)
consul_ui_rule.IpProtocol = 'tcp'
t.add_resource(consul_ui_rule)

# ssh for each home egress point
home_ssh_rules = []
for (ip, name) in home_egress_ips:
    rule = SecurityGroupIngress(name)
    rule.CidrIp = ip
    rule.FromPort = 22
    rule.ToPort = 22
    rule.GroupId = Ref(home_ssh)
    rule.IpProtocol = 'tcp'
    home_ssh_rules.append(rule)
    t.add_resource(rule)

# load balancer
elb_listener_80 = Listener(config['name'] + 'Ssl')
elb_listener_80.InstancePort = 80
elb_listener_80.LoadBalancerPort = 80
elb_listener_80.Protocol = 'HTTP'
elb_listener_80.InstanceProtocol = 'HTTP'

load_balancer = LoadBalancer(config['name'] + "Elb")
load_balancer.CrossZone = True
load_balancer.Listeners = [elb_listener_80]
load_balancer.Subnets = [Ref(subnet.title) for subnet in app_subnets]
t.add_resource(load_balancer)

# launch configuration for consul server
consul_block_device = EBSBlockDevice(config['name'] + 'Ebs')
consul_block_device.DeleteOnTermination = config['consul_launch_config']['block_device']['delete_on_termination']

consul_block_device_mapping = BlockDeviceMapping(config['name'] + 'ConsulBlockDeviceMapping')
consul_block_device_mapping.DeviceName = '/dev/sda1'
consul_block_device_mapping.Ebs = consul_block_device

consul_launch_config = LaunchConfiguration(config['name'] + 'ConsulLaunchConfig')
consul_launch_config.AssociatePublicIpAddress = True
consul_launch_config.EbsOptimized = config['consul_launch_config']['ebs_optimized']
consul_launch_config.ImageId = config['consul_launch_config']['image_id']
consul_launch_config.KeyName = config['consul_launch_config']['key_name']
consul_launch_config.InstanceType = config['consul_launch_config']['instance_type']
consul_launch_config.BlockDeviceMappings = [consul_block_device_mapping]
consul_launch_config.SecurityGroups = [Ref(config['name'] + 'homeSsh'), Ref(consul_sg)]
t.add_resource(consul_launch_config)

# auto scale group for consul server
consul_asg = AutoScalingGroup(config['name'] + 'ConsulAsg')
consul_asg.AvailabilityZones = config['consul_asg']['availability_zones']
consul_asg.LaunchConfigurationName = Ref(consul_launch_config)
consul_asg.MaxSize = config['consul_asg']['max_size']
consul_asg.MinSize = config['consul_asg']['min_size']
consul_asg.VPCZoneIdentifier = [Ref(subnet.title) for subnet in app_subnets]
name_tag = {'Key': 'Name', 'Value': config['consul_asg']['instance_name'], 'PropagateAtLaunch': True}
consul_asg.Tags = [name_tag]
t.add_resource(consul_asg)

# launch configuration for application
block_device = EBSBlockDevice(config['name'] + 'Ebs')
block_device.DeleteOnTermination = config['app_launch_config']['block_device']['delete_on_termination']

block_device_mapping = BlockDeviceMapping(config['name'] + 'BlockDeviceMapping')
block_device_mapping.DeviceName = '/dev/sda1'
block_device_mapping.Ebs = block_device

app_launch_config = LaunchConfiguration(config['name'] + 'LaunchConfig')
app_launch_config.AssociatePublicIpAddress = True
app_launch_config.EbsOptimized = config['app_launch_config']['ebs_optimized']
app_launch_config.ImageId = config['app_launch_config']['image_id']
app_launch_config.KeyName = config['app_launch_config']['key_name']
app_launch_config.InstanceType = config['app_launch_config']['instance_type']
app_launch_config.BlockDeviceMappings = [block_device_mapping]
app_launch_config.SecurityGroups = [Ref(config['name'] + 'homeSsh'), Ref(consul_sg)]
t.add_resource(app_launch_config)

# auto scale group for application
app_asg = AutoScalingGroup(config['name'] + 'Asg')
app_asg.AvailabilityZones = config['app_asg']['availability_zones']
app_asg.LaunchConfigurationName = Ref(app_launch_config)
app_asg.LoadBalancerNames = [Ref(load_balancer)]
app_asg.MaxSize = config['app_asg']['max_size']
app_asg.MinSize = config['app_asg']['min_size']
app_asg.VPCZoneIdentifier = [Ref(subnet.title) for subnet in app_subnets]
name_tag = {'Key': 'Name', 'Value': config['app_asg']['instance_name'], 'PropagateAtLaunch': True}
app_asg.Tags = [name_tag]
t.add_resource(app_asg)

# print the template to screen
print(t.to_json())

# write to file
cloudformation_file = 'final-project.json'
f = open(cloudformation_file, 'w')
f.write(t.to_json())
f.close()
