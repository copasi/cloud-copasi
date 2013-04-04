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
from web_interface import models
from web_interface.aws import aws_tools, ec2_config
from web_interface.models import EC2Instance, VPC, EC2KeyPair, AMI, CondorPool, ElasticIP
import sys, os
from exceptions import Exception
from time import sleep
import settings

def get_ami(ec2_connection, ami):
    assert isinstance(ec2_connection, EC2Connection)
    assert isinstance(ami, models.AMI)
    
    ami = ec2_connection.get_image(ami.image_id)
    return ami

def get_active_ami(ec2_connection):
    ami=models.AMI.objects.get(active=True)
    return get_ami(ec2_connection, ami)


def create_key_pair(pool):
    """Create a keypair and store it in the users storage directory
    """
    
    assert isinstance(pool, models.CondorPool)
    vpc_connection, ec2_connection = aws_tools.create_connections(pool.vpc.access_key)
    name = pool.name + '_keypair'
    key = ec2_connection.create_key_pair(name)
    
    #The directory where we store the ssh keypairs. Must be writable
    filepath = settings.KEYPAIR_FILEPATH
    
    path=os.path.join(filepath, name + '.pem')
    key.save(filepath)
    
    key_pair = EC2KeyPair(name=name, path=path)
    
    key_pair.save()
    return key_pair

def launch_pool(condor_pool):
    """
    Launch a Condor pool with the definitions provided by the condor_pool object
    """
    
    
    assert isinstance(condor_pool, CondorPool)
    
    #Initiate the connection    
    vpc_connection, ec2_connection = aws_tools.create_connections(condor_pool.vpc.access_key)
    
    ami = get_active_ami(ec2_connection)
    
    #Launch the master instance
    #Add the pool details to the launch string
    master_launch_string = ec2_config.MASTER_LAUNCH_STRING % (settings.HOST,
                                                              condor_pool.id,
                                                              condor_pool.secret_key,
                                                              condor_pool.vpc.access_key.access_key_id,
                                                              condor_pool.vpc.access_key.secret_key)
    #And launch
    master_reservation = ec2_connection.run_instances(ami.id,
                                               key_name=condor_pool.key_pair.name,
                                               instance_type=condor_pool.initial_instance_type,
                                               subnet_id=condor_pool.vpc.subnet_id,
                                               security_group_ids=[condor_pool.vpc.master_group_id],
                                               user_data=master_launch_string,
                                               min_count=1,#Only 1 instance needed
                                               max_count=1,
                                               )
    ec2_instances = []

    master_instance = master_reservation.instances[0]
    master_ec2_instance = EC2Instance()
    master_ec2_instance.condor_pool = condor_pool
    master_ec2_instance.instance_id = master_instance.id
    master_ec2_instance.instance_type = condor_pool.initial_instance_type
    master_ec2_instance.instance_role = 'master'
    
    
    master_ec2_instance.save()
    ec2_instances.append(master_ec2_instance)

    condor_pool.master = master_ec2_instance
    condor_pool.save()
    
    #wait until the master has a private ip address
    #sleep in beween
    sleep_time=2
    max_retrys=10
    current_try=0
    while master_ec2_instance.get_private_ip() == None and current_try<max_retrys:
        sleep(sleep_time)
        current_try+=1
    
    if condor_pool.size > 0:
        worker_reservation = ec2_connection.run_instances(ami.id,
                                                   key_name=condor_pool.key_pair.name,
                                                   instance_type=condor_pool.initial_instance_type,
                                                   subnet_id=condor_pool.vpc.subnet_id,
                                                   security_group_ids=[condor_pool.vpc.worker_group_id],
                                                   user_data=ec2_config.WORKER_LAUNCH_STRING % condor_pool.master.get_private_ip(),
                                                   min_count=condor_pool.size,
                                                   max_count=condor_pool.size,
                                                   )

        instances = worker_reservation.instances
        for instance in instances:
            ec2_instance = EC2Instance()
            ec2_instance.condor_pool = condor_pool
            ec2_instance.instance_id = instance.id
            ec2_instance.instance_type = condor_pool.initial_instance_type
            ec2_instance.instance_role = 'worker'
            
            ec2_instance.save()
            
            ec2_instances.append(ec2_instance)
        
        
    #Assign an elastic IP to the master instance
    assign_ip_address(master_ec2_instance)
    
    return ec2_instances


def terminate_pool(condor_pool):
    assert isinstance(condor_pool, CondorPool)
    
    #Keep a track of the following errors
    errors=[]
    #First, create an ec2_connection object
    vpc_connection, ec2_connection = aws_tools.create_connections(condor_pool.vpc.access_key)
    assert isinstance(ec2_connection, EC2Connection)
    instances = EC2Instance.objects.filter(condor_pool=condor_pool)
    
    
    #Dissassociate the IP address of the master instance and release it
    try:
        if condor_pool.master.elasticip != None:
            ec2_connection.disassociate_address(association_id=condor_pool.master.elasticip.association_id)
            ec2_connection.release_address(allocation_id=condor_pool.master.elasticip.allocation_id)
            condor_pool.master.elasticip.delete()
    except Exception, e:
        errors.append(e)

    
    instance_ids = [instance.instance_id for instance in instances]
    
    try:
        ec2_connection.terminate_instances(instance_ids)
    except Exception, e:
        errors.append(e)
    
    key_pair = condor_pool.key_pair
    
    try:
        ec2_connection.delete_key_pair(key_pair.name)
    except Exception, e:
        errors.append(e)
    try:
        os.remove(key_pair.path)
    except:
        pass
    condor_pool.delete()
    key_pair.delete()
    #Flatten the errors into 1 list
    
    return errors

def assign_ip_address(ec2_instance):
    """Assign a public IP address to the ec2 instance
    """
    #Check to see if there are any unassigned IP addresses:    
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_instance.condor_pool.vpc.access_key)

    assert isinstance(ec2_instance, EC2Instance)
    ips = ElasticIP.objects.filter(vpc=ec2_instance.condor_pool.vpc).filter(instance=None)
    
    if ips.count() > 0:
        #Use the first IP address
        elastic_ip=ips[0]
    else:
        #We need to allocate a new ip address first
        address=ec2_connection.allocate_address('vpc')
        
        elastic_ip = ElasticIP()
        elastic_ip.allocation_id = address.allocation_id
        elastic_ip.public_ip = address.public_ip
        elastic_ip.vpc = ec2_instance.condor_pool.vpc
    
    #Wait until the instance is in state running, then associate the ip address
    #Sleep 5 seconds between attempts
    #Max 6 attemps...
    sleep_time=5
    max_attempts=6
    attempt_count=0
    while attempt_count < max_attempts:
        if ec2_instance.get_state() == 'running':
            break
        else:
            sleep(sleep_time)
            attempt_count +=1
    
    assert ec2_connection.associate_address(instance_id=ec2_instance.instance_id, allocation_id=elastic_ip.allocation_id)
    elastic_ip.instance=ec2_instance
    
    #Use an inelegent workaround to get the association id of the address, since the api doesn't tell us this
    #Reload the address object
    new_address = ec2_connection.get_all_addresses(allocation_ids=[elastic_ip.allocation_id])[0]
    
    elastic_ip.association_id=new_address.association_id
    
    elastic_ip.save()

        
    return elastic_ip

def release_ip_address(ec2_instance):
    """Dissassociate and release the public IP address of the ec2 instance
    """
    assert isinstance(ec2_instance, EC2Instance)
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_instance.condor_pool.vpc.access_key)
    
    errors=[]
    try:
        ip = ElasticIP.objects.get(instance=ec2_instance)

        ec2_connection.disassociate_address(association_id=ip.association_id)
        ec2_connection.release_addresss(allocation_id=ip.allocation_id)
    
    except Exception, e:
        errors.append(e)
     
    try:
        ip.delete()
    except Exception, e:
        errors.append(e)
    
    return errors
