#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
import boto3
import logging
from web_interface import models
import boto.exception
import sys, os
import time
IP_RANGE='10.0.0.0'
VPC_CIDR_BLOCK = IP_RANGE + '/16'
SUBNET_CIDR_BLOCK = IP_RANGE + '/16'
SSH_PORT = 22
CONDOR_FROM_PORT = 9600
CONDOR_TO_PORT = 9700
ALLOW_ALL_TRAFFIC = True #Allow only specific condor ports, or allow all traffic (for debuging only)


log = logging.getLogger(__name__)
slog = logging.getLogger("special")

def create_vpc(key, vpc_connection, ec2_connection):

    """
    assert isinstance(ec2_connection, EC2Connection)
    assert isinstance(vpc_connection, VPCConnection)

    vpc = vpc_connection.create_vpc(VPC_CIDR_BLOCK)
    time.sleep(5)
    #This also creates a DHCP options set associated with the VPC. Leave this unchanged
    #Create a subnet
    subnet = vpc_connection.create_subnet(vpc.id, SUBNET_CIDR_BLOCK)
    time.sleep(5)
    #Create an internet gateway device
    internet_gateway = vpc_connection.create_internet_gateway()
    time.sleep(5)
    #Attach the internet gateway to the VPC
    vpc_connection.attach_internet_gateway(internet_gateway.id, vpc.id)
    time.sleep(5)
    #Create a route table for the subnet containing 2 entries
    route_table = vpc_connection.create_route_table(vpc.id)
    time.sleep(5)
    #Entry 1: 10.0.0.0/16 local
    #Created by default
    #Entry 2: 0.0.0.0/0 internet_gateway
    vpc_connection.create_route(route_table.id, '0.0.0.0/0', gateway_id=internet_gateway.id)
    time.sleep(5)
    #Associate the route table with the subnet
    route_table_association_id = vpc_connection.associate_route_table(route_table.id, subnet.id)
    time.sleep(5)

    #Set up the security groups
    master_sg_name = 'condor_master_' + str(vpc.id)
    worker_sg_name = 'condor_worker_' + str(vpc.id)
    master_group = ec2_connection.create_security_group(master_sg_name, 'created_by_cloud_copasi', vpc.id)
    worker_group = ec2_connection.create_security_group(worker_sg_name, 'created_by_cloud_copasi', vpc.id)
    time.sleep(5)
    if not ALLOW_ALL_TRAFFIC:
        #Set up the master security group
        master_group.authorize(ip_protocol='TCP', from_port=22, to_port=22, cidr_ip='0.0.0.0/0')
        master_group.authorize(ip_protocol='TCP', from_port=9600, to_port=9700, cidr_ip=VPC_CIDR_BLOCK)
        master_group.authorize(ip_protocol='UDP', from_port=9600, to_port=9700, cidr_ip=VPC_CIDR_BLOCK)
        time.sleep(5)
        #Set up the worker security group
        worker_group.authorize(ip_protocol='TCP', from_port=22, to_port=22, cidr_ip=VPC_CIDR_BLOCK)
        worker_group.authorize(ip_protocol='TCP', from_port=9600, to_port=9700, cidr_ip=VPC_CIDR_BLOCK)
        worker_group.authorize(ip_protocol='UDP', from_port=9600, to_port=9700, cidr_ip=VPC_CIDR_BLOCK)
    else:
        #Set up the master security group and worker group to allow all traffic
        master_group.authorize(ip_protocol='TCP', from_port=0, to_port=65535, cidr_ip='0.0.0.0/0')
        master_group.authorize(ip_protocol='UDP', from_port=0, to_port=65535, cidr_ip='0.0.0.0/0')
        time.sleep(5)
        #Set up the worker security group
        worker_group.authorize(ip_protocol='TCP', from_port=0, to_port=65535, cidr_ip='0.0.0.0/0')
        worker_group.authorize(ip_protocol='UDP', from_port=0, to_port=65535, cidr_ip='0.0.0.0/0')

    vpc_model = models.VPC(
                           access_key = key,
                           vpc_id = vpc.id,
                           subnet_id = subnet.id,
                           internet_gateway_id = internet_gateway.id,
                           route_table_id = route_table.id,
                           route_table_association_id=route_table_association_id,
                           master_group_id = master_group.id,
                           worker_group_id = worker_group.id,
                           )


    vpc_model.save()

    return vpc_model"""
    # commented by fizza
    slog.debug("entered create vpc method")
    vpc = vpc_connection.create_vpc(CidrBlock=VPC_CIDR_BLOCK)
    time.sleep(5)
    slog.debug("vpc created with cidr block")
    slog.debug("vpc: " + str(vpc))
    #This also creates a DHCP options set associated with the VPC. Leave this unchanged
    #Create a subnet
    #comented
    # subnet = vpc_connection.create_subnet(vpc.id, SUBNET_CIDR_BLOCK)
    subnet = vpc_connection.create_subnet(VpcId=vpc['Vpc']['VpcId'], CidrBlock=SUBNET_CIDR_BLOCK)
    time.sleep(5)
    #Create an internet gateway device
    internet_gateway = vpc_connection.create_internet_gateway()
    time.sleep(5)
    #Attach the internet gateway to the VPC
    vpc_connection.attach_internet_gateway(InternetGatewayId=internet_gateway['InternetGateway']['InternetGatewayId'], VpcId=vpc['Vpc']['VpcId'])
    time.sleep(5)
    #Create a route table for the subnet containing 2 entries
    route_table = vpc_connection.create_route_table(VpcId=vpc['Vpc']['VpcId'])['RouteTable']
    time.sleep(5)
    #Entry 1: 10.0.0.0/16 local
    #Created by default
    #Entry 2: 0.0.0.0/0 internet_gateway
    vpc_connection.create_route(RouteTableId=route_table['RouteTableId'], DestinationCidrBlock='0.0.0.0/0', GatewayId=internet_gateway['InternetGateway']['InternetGatewayId'])
    time.sleep(5)
    #Associate the route table with the subnet
    route_table_association_id = vpc_connection.associate_route_table(RouteTableId=route_table['RouteTableId'], SubnetId=subnet['Subnet']['SubnetId'])['AssociationId']
    time.sleep(5)

    #Set up the security groups
    master_sg_name = 'condor_master_' + str(vpc['Vpc']['VpcId'])
    worker_sg_name = 'condor_worker_' + str(vpc['Vpc']['VpcId'])
    master_group = ec2_connection.create_security_group(GroupName=master_sg_name, Description='created_by_cloud_copasi', VpcId=vpc['Vpc']['VpcId'])
    worker_group = ec2_connection.create_security_group(GroupName=worker_sg_name, Description='created_by_cloud_copasi', VpcId=vpc['Vpc']['VpcId'])
    time.sleep(5)
    slog.debug('security groups created')
    if not ALLOW_ALL_TRAFFIC:
        #Set up the master security group
        ec2_connection.authorize_security_group_ingress(GroupId=master_group['GroupId'], IpPermissions = [
            {'IpProtocol':'TCP', 'FromPort':22, 'ToPort':22, 'IpRanges':[{'CidrIp':'0.0.0.0/0'}]}
            ])
        ec2_connection.authorize_security_group_ingress(GroupId=master_group['GroupId'], IpPermissions = [
            {"IpProtocol":'TCP', "FromPort":9600, "ToPort":9700, 'IpRanges':[{"CidrIp":VPC_CIDR_BLOCK}]}
            ])
        ec2_connection.authorize_security_group_ingress(GroupId=master_group['GroupId'], IpPermissions = [
        {"IpProtocol":'UDP', "FromPort":9600, "ToPort":9700, "IpRanges":[{"CidrIp":VPC_CIDR_BLOCK}]}
        ])
        time.sleep(5)
        #Set up the worker security group
        ec2_connection.authorize_security_group_ingress(GroupId=worker_group['GroupId'], IpPermissions = [
        {"IpProtocol":'TCP', "FromPort":22, "ToPort":22, 'IpRanges':[{"CidrIp":VPC_CIDR_BLOCK}]}
        ])
        ec2_connection.authorize_security_group_ingress(GroupId=worker_group['GroupId'], IpPermissions = [
        {"IpProtocol":'TCP', "FromPort":9600, "ToPort":9700, "IpRanges":[{"CidrIp":VPC_CIDR_BLOCK}]}
        ])
        ec2_connection.authorize_security_group_ingress(GroupId=worker_group['GroupId'], IpPermissions = [
        {"IpProtocol":'UDP', "FromPort":9600, "ToPort":9700, "IpRanges":[{"CidrIp":VPC_CIDR_BLOCK}]}
        ])
    else:
        #Set up the master security group and worker group to allow all traffic
        ec2_connection.authorize_security_group_ingress(GroupId=master_group['GroupId'], IpPermissions = [
        {"IpProtocol":'TCP', "FromPort":0, "ToPort":65535, "IpRanges":[{"CidrIp":'0.0.0.0/0'}]}
        ])
        ec2_connection.authorize_security_group_ingress(GroupId=master_group['GroupId'], IpPermissions = [
        {"IpProtocol":'UDP', "FromPort":0, "ToPort":65535, "IpRanges":[{"CidrIp":'0.0.0.0/0'}]}
        ])
        # Egress connections
        ec2_connection.authorize_security_group_egress(GroupId=master_group['GroupId'], IpPermissions = [
        {"IpProtocol":'TCP', "FromPort":0, "ToPort":65535, "IpRanges":[{"CidrIp":'0.0.0.0/0'}]}
        ])
        ec2_connection.authorize_security_group_egress(GroupId=master_group['GroupId'], IpPermissions = [
        {"IpProtocol":'UDP', "FromPort":0, "ToPort":65535, "IpRanges":[{"CidrIp":'0.0.0.0/0'}]}
        ])
        time.sleep(5)
        #Set up the worker security group
        ec2_connection.authorize_security_group_ingress(GroupId=worker_group['GroupId'], IpPermissions = [
        {"IpProtocol":'TCP', "FromPort":0, "ToPort":65535, "IpRanges":[{"CidrIp":'0.0.0.0/0'}]}
        ])
        ec2_connection.authorize_security_group_ingress(GroupId=worker_group['GroupId'], IpPermissions = [
        {"IpProtocol":'UDP', "FromPort":0, "ToPort":65535, "IpRanges":[{"CidrIp":'0.0.0.0/0'}]}
        ])
        # Egress connections
        ec2_connection.authorize_security_group_egress(GroupId=worker_group['GroupId'], IpPermissions = [
        {"IpProtocol":'TCP', "FromPort":0, "ToPort":65535, "IpRanges":[{"CidrIp":'0.0.0.0/0'}]}
        ])
        ec2_connection.authorize_security_group_egress(GroupId=worker_group['GroupId'], IpPermissions = [
        {"IpProtocol":'UDP', "FromPort":0, "ToPort":65535, "IpRanges":[{"CidrIp":'0.0.0.0/0'}]}
        ])

    slog.debug('security authorized')
    vpc_model = models.VPC(
                           access_key = key,
                           vpc_id = vpc['Vpc']['VpcId'],
                           subnet_id = subnet['Subnet']['SubnetId'],
                           internet_gateway_id = internet_gateway['InternetGateway']['InternetGatewayId'],
                           route_table_id = route_table['RouteTableId'],
                           route_table_association_id=route_table_association_id,
                           master_group_id = master_group['GroupId'],
                           worker_group_id = worker_group['GroupId'],
                           )

    slog.debug(vpc['Vpc']['VpcId'] + " " + subnet['Subnet']['SubnetId']+ " " + internet_gateway['InternetGateway']['InternetGatewayId']+ " " +route_table['RouteTableId']+ " " +route_table_association_id+ " " +master_group['GroupId']+ " " +worker_group['GroupId'])
    slog.debug('model saved')
    vpc_model.save()

    return vpc_model

def delete_vpc(vpc, vpc_connection, ec2_connection):

    assert isinstance(vpc, models.VPC)

    errors = []

    try:
        ec2_connection.delete_security_group(GroupId=vpc.master_group_id)
    except Exception as e:
        errors.append(e)

    try:
        ec2_connection.delete_security_group(GroupId=vpc.worker_group_id)
    except Exception as e:
        errors.append(e)

    try:
        vpc_connection.disassociate_route_table(AssociationId=vpc.route_table_association_id)
    except Exception as e:
        errors.append(e)

    try:
        vpc_connection.delete_route_table(RouteTableId=vpc.route_table_id)
    except Exception as e:
        errors.append(e)

    try:
        vpc_connection.detach_internet_gateway(InternetGatewayId=vpc.internet_gateway_id, VpcId=vpc.vpc_id)
    except Exception as e:
        errors.append(e)

    try:
        vpc_connection.delete_internet_gateway(InternetGatewayId=vpc.internet_gateway_id)
    except Exception as e:
        errors.append(e)

    try:
        vpc_connection.delete_subnet(SubnetId=vpc.subnet_id)
    except Exception as e:
        errors.append(e)

    try:
        vpc_connection.delete_vpc(VpcId=vpc.vpc_id)
    except Exception as e:
        errors.append(e)

    vpc.delete()

    return errors
