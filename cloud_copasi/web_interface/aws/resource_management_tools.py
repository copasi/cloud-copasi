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
    s3_tools, task_tools
from cloud_copasi.web_interface.models import EC2Instance, VPC, EC2KeyPair, AMI, CondorPool, ElasticIP,\
    AWSAccessKey, Task
import sys, os
from exceptions import Exception
from time import sleep
from cloud_copasi import settings
from boto import sqs
import logging

log = logging.getLogger(__name__)
#Extra resources are those which we have no record of launching

class ResourceOverview():
    
    
    def __init__(self, ec2_instances=None, elastic_ips=None, s3_buckets=None):
        
        #List of instance ids
        self.ec2_instances = []
        if ec2_instances:
            self.ec2_instances += ec2_instances
        
        #List of dicts: association id and allocation id
        self.elastic_ips = []
        if elastic_ips:
            self.elastic_ips += elastic_ips
        
        #List of s3 bucket names
        self.s3_buckets = []
        if s3_buckets:
            self.s3_buckets += s3_buckets
        
    def __add__(self, x):
        assert isinstance(x,ResourceOverview)
        
        return ResourceOverview(ec2_instances = list(set(self.ec2_instances) + set(x.ec2_instances)),
                                elastic_ips = list(set(self.elastic_ips) + set(x.elastic_ips)),
                                s3_buckets = list(set(self.s3_buckets) + set(x.s3_buckets)),
                                )
            
            
    def __sub__(self, x):
        assert isinstance(x,ResourceOverview)
        return ResourceOverview(ec2_instances = list(set(self.ec2_instances) - set(x.ec2_instances)),
                                elastic_ips = list(set(self.elastic_ips) - set(x.elastic_ips)),
                                s3_buckets = list(set(self.s3_buckets) - set(x.s3_buckets)),
                                )
        
        
    def add_ec2_instance(self, key, instance_id):
        self.ec2_instances.append((key, instance_id))
        
    def add_elastic_ip(self, key, allocation_id, association_id=None, public_ip=None):
        self.elastic_ips.append((key, allocation_id, association_id, public_ip))

            
    def add_s3_bucket(self, key, bucket_name):
        self.s3_buckets.append((key, bucket_name ))
        
    def is_empty(self):
        return len(self.ec2_instances)==0 and len(self.elastic_ips)==0 and len(self.s3_buckets)==0
            
def get_remote_resources(user, key=None):
    """Return an overview of all the aws resources in use
    """
    if key:
        keys=[key]
    else:
        keys = AWSAccessKey.objects.filter(user=user)
    
    overview = ResourceOverview()
    
    for key in keys:
        try:
            vpc_connection, ec2_connection =aws_tools.create_connections(key)
            s3_connection = s3_tools.create_s3_connection(key)
            
            #Get ec2 count
            instance_reservations=ec2_connection.get_all_instances()
            for reservation in instance_reservations:
                for instance in reservation.instances:
                    if instance.state == 'pending' or instance.state=='running':
                        overview.add_ec2_instance(key, instance.id)
            
        except Exception, e:
            log.exception(e)
        
        try:
            addresses = ec2_connection.get_all_addresses()
            for address in addresses:
                if address.allocation_id == None:
                    overview.add_elastic_ip(key, None, None, address.public_ip)
                else:
                    overview.add_elastic_ip(key, address.allocation_id, address.association_id, None)
                
        except Exception, e:
            log.exception(e)
        
        try:
            s3_buckets = s3_connection.get_all_buckets()
            for bucket in s3_buckets:
                overview.add_s3_bucket(key, bucket.name)
            
        except Exception, e:
            log.exception(e)
        
    
    
    return overview



def get_local_resources(user, key=None):
    
    overview = ResourceOverview()
    
    for condor_pool in CondorPool.objects.filter(vpc__access_key__user=user):
        ec2_tools.refresh_pool(condor_pool)
    
    if key:
        keys=[key]
    else:
        keys=AWSAccessKey.objects.filter(user=user)
    
    for key in keys:
        #EC2 instances
        ec2_instances = EC2Instance.objects.filter(condor_pool__vpc__access_key=key)
        log.debug('all_instances')
        log.debug(ec2_instances)
        log.debug('pending instances')
        log.debug(ec2_instances.filter(state='pending'))
        log.debug('running instances')
        log.debug(ec2_instances.filter(state='running'))
        running_instances = ec2_instances.filter(state='pending') | ec2_instances.filter(state='running')# | ec2_instances.filter(state='shutting-down')
        
        for instance in running_instances:
            overview.add_ec2_instance(key, instance.instance_id)
        
        
        #Elastic IPs
        elastic_ips = ElasticIP.objects.all()
        
        for elastic_ip in elastic_ips:
            overview.add_elastic_ip(key, elastic_ip.allocation_id, elastic_ip.association_id, None)
        
        #S3 buckets. Should be two for every non-deleted task
        #Get non-deleted tasks
        tasks = Task.objects.exclude(status='deleted')
        
        for task in tasks:
            overview.add_s3_bucket(key, task.get_outgoing_bucket_name())
            overview.add_s3_bucket(key, task.get_incoming_bucket_name())
        
    return overview

def get_recognized_resources(user, key=None):
    """Return an overview of any aws resources we don't have a record of'
    """
    
    return get_local_resources(user, key)

def get_unrecognized_resources(user, key=None):
    """Return an overview of any aws resources we don't have a record of'
    """
    
    recognized = get_recognized_resources(user, key)
    
    remote = get_remote_resources(user, key)
    
    unrecognized = remote-recognized
    return unrecognized


def terminate_resources(user, resources):
    """Terminate the AWS resources here.
    These will not correspond to any local model
    """
    assert isinstance(resources, ResourceOverview)
    
    ec2_instances={}
    elastic_ips={}
    s3_buckets={}
    
    #Build up dicts to contain resources indexed by key 
    
    for key, instance_id in resources.ec2_instances:
        assert key.user == user
        if key in ec2_instances:
            ec2_instances[key].append(instance_id)
        else:
            ec2_instances[key] = [instance_id]
            
    for key, allocation_id, association_id, public_ip in resources.elastic_ips:
        assert key.user == user
        if key in elastic_ips:
            elastic_ips[key].append((allocation_id, association_id, public_ip))
        else:
            elastic_ips[key] = [(allocation_id, association_id, public_ip)]
            
    for key, bucket_name in resources.s3_buckets:
        assert key.user == user
        if key in s3_buckets:
            s3_buckets[key].append(bucket_name)
        else:
            s3_buckets[key] = [bucket_name]
        
        
    #Release IPs    
    for key in elastic_ips:
        for allocation_id, association_id, public_ip in elastic_ips[key]:
            log.debug('Releasing IP address with allocation ID %s'%allocation_id)
            try:
                if public_ip:
                    ec2_tools.release_ip_address(key, None, None, public_ip)
                else:
                    ec2_tools.release_ip_address(key, allocation_id, association_id, None)
            except Exception, e:
                log.exception(e)
                
                
    #Terminate EC2 instances
    for key in ec2_instances:
        log.debug('Terminating %d instances for key %s' %(len(ec2_instances[key]), key.name))
        try:
            vpc_connection, ec2_connection = aws_tools.create_connections(key)
            ec2_connection.terminate_instances(ec2_instances[key])
        except Exception, e:
            log.exception(e)
    

    #Delete buckets
    for key in s3_buckets:
        for bucket_name in s3_buckets[key]:
            try:
                log.debug('Deleting bucket %s' %bucket_name)
                s3_connection = s3_tools.create_s3_connection(key)
                bucket = s3_connection.get_bucket(bucket_name)
                task_tools.delete_bucket(bucket)
            except Exception, e:
                log.exception(e)
                
def health_check(user, key=None):
    """Perform a health check on all AWS resources
    """
    condor_pools = CondorPool.objects.filter(vpc__access_key__user=user)
    for condor_pool in condor_pools:
        health = condor_pool.get_health()
        if health != 'healthy': return health
    return 'healthy'