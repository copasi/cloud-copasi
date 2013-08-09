#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from boto.vpc import VPCConnection
from boto.ec2 import EC2Connection
from boto.s3.connection import S3Connection
from cloud_copasi.web_interface import models
from cloud_copasi.web_interface.aws import s3_tools
import boto.exception
import sys, os
import time
IP_RANGE='10.0.0.0'
VPC_CIDR_BLOCK = IP_RANGE + '/16'
SUBNET_CIDR_BLOCK = IP_RANGE + '/24'
SSH_PORT = 22
CONDOR_FROM_PORT = 9600
CONDOR_TO_PORT = 9700

def create_vpc(key, vpc_connection, ec2_connection):
    
    
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
    #Set up the master security group
    master_group.authorize(ip_protocol='TCP', from_port=22, to_port=22, cidr_ip='0.0.0.0/0')
    master_group.authorize(ip_protocol='TCP', from_port=9600, to_port=9700, cidr_ip=VPC_CIDR_BLOCK)
    master_group.authorize(ip_protocol='UDP', from_port=9600, to_port=9700, cidr_ip=VPC_CIDR_BLOCK)
    time.sleep(5)
    #Set up the worker security group
    worker_group.authorize(ip_protocol='TCP', from_port=22, to_port=22, cidr_ip=VPC_CIDR_BLOCK)
    worker_group.authorize(ip_protocol='TCP', from_port=9600, to_port=9700, cidr_ip=VPC_CIDR_BLOCK)
    worker_group.authorize(ip_protocol='UDP', from_port=9600, to_port=9700, cidr_ip=VPC_CIDR_BLOCK)
    
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
    
    return vpc_model

def delete_vpc(vpc, vpc_connection, ec2_connection):
    
    assert isinstance(vpc, models.VPC)
    assert isinstance(ec2_connection, EC2Connection)
    assert isinstance(vpc_connection, VPCConnection)
    
    s3_connection=s3_tools.create_s3_connection(vpc.access_key)
    
    errors = []
    
    try:
        ec2_connection.delete_security_group(group_id=vpc.master_group_id)
    except Exception, e:
        errors.append(e)
    
    try:
        ec2_connection.delete_security_group(group_id=vpc.worker_group_id)
    except Exception, e:
        errors.append(e)
    
    try:
        vpc_connection.disassociate_route_table(vpc.route_table_association_id)
    except Exception, e:
        errors.append(e)
    
    try:
        vpc_connection.delete_route_table(vpc.route_table_id)
    except Exception, e:
        errors.append(e)
    
    try:
        vpc_connection.detach_internet_gateway(vpc.internet_gateway_id, vpc.vpc_id)
    except Exception, e:
        errors.append(e)
    
    try:
        vpc_connection.delete_internet_gateway(vpc.internet_gateway_id)
    except Exception, e:
        errors.append(e)
    
    try:
        vpc_connection.delete_subnet(vpc.subnet_id)
    except Exception, e:
        errors.append(e)
    
    try:
        vpc_connection.delete_vpc(vpc.vpc_id)
    except Exception, e:
        errors.append(e)
    
#     try:
#         s3_connection.delete_bucket(vpc.s3_bucket_name)
#     except Exception, e:
#         errors.append(e)

    vpc.delete()
    
    return errors

