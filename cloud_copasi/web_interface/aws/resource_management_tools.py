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
from boto.ec2.instance import Instance
from cloud_copasi.web_interface import models
from cloud_copasi.web_interface.aws import aws_tools, ec2_config, ec2_tools,\
    s3_tools
from cloud_copasi.web_interface.models import EC2Instance, VPC, EC2KeyPair, AMI, CondorPool, ElasticIP,\
    AWSAccessKey
import sys, os
from exceptions import Exception
from time import sleep
from cloud_copasi import settings
from boto import sqs
import logging

log = logging.getLogger(__name__)
#Extra resources are those which we have no record of launching

class ResourceOverview():
    def __init__(self,
                 ec2_instances=0,
                 elastic_ips=0,
                 s3_buckets=0,
                 ):
        self.ec2_instances = ec2_instances
        self.elastic_ips = elastic_ips
        self.s3_buckets = s3_buckets

def get_aws_resources(user):
    """Return an overview of all the aws resources in use
    """
    
    keys = AWSAccessKey.objects.filter(user=user)
    for key in keys:
        
        ec2_count = 0
        elastic_ip_count=0
        vpc_count = 0
        s3_bucket_count = 0
        
        try:
            vpc_connection, ec2_connection =aws_tools.create_connections(key)
            s3_connection = s3_tools.create_s3_connection(key)
            
            #Get ec2 count
            instance_reservations=ec2_connection.get_all_instances()
            for reservation in instance_reservations:
                ec2_count += len(reservation.instances)
        except Exception, e:
            log.exception(e)
        
        try:
            addresses = ec2_connection.get_all_addresses()
            elastic_ip_count = len(addresses)
        except Exception, e:
            log.exception(e)
        
        try:
            s3_buckets = s3_connection.get_all_buckets()
            s3_bucket_count=len(s3_buckets)
            
        except Exception, e:
            log.exception(e)
        
    
    overview = ResourceOverview(ec2_instances=ec2_count,
                                elastic_ips = elastic_ip_count,
                                s3_buckets=s3_bucket_count,
                                )
    
    return overview

def get_unrecognised_resources(user):
    """Return an overview of any aws resources we don't have a record of'
    """
    
    overview = ResourceOverview()
    
    
    
    return overview

