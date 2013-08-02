#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from boto.vpc import VPCConnection
from boto.ec2 import EC2Connection, cloudwatch
from boto.ec2.instance import Instance
from cloud_copasi.web_interface import models
from cloud_copasi.web_interface.aws import aws_tools, ec2_config
from cloud_copasi.web_interface.models import EC2Instance, VPC, EC2KeyPair, AMI, EC2Pool, ElasticIP, Task
import sys, os
from exceptions import Exception
from time import sleep
from cloud_copasi import settings
from boto import sqs
import logging
import datetime
from django.utils.timezone import now as utcnow
from django.utils.timezone import utc
from django.core.urlresolvers import reverse_lazy
import subprocess

log = logging.getLogger(__name__)

def get_ami(ec2_connection, ami):
    assert isinstance(ec2_connection, EC2Connection)
    assert isinstance(ami, models.AMI)
    
    ami = ec2_connection.get_image(ami.image_id)
    return ami

def get_active_ami(ec2_connection):
    ami=models.AMI.objects.get(active=True)
    return get_ami(ec2_connection, ami)

def refresh_pool(ec2_pool):
    """Refresh the state of each instance in a ec2 pool
    """
    log.debug('refreshing status of pool %s' % ec2_pool.name)
    difference = utcnow() - ec2_pool.last_update_time.replace(tzinfo=utc)
    log.debug('Time difference %s' % str(difference))
    if difference < datetime.timedelta(seconds=3):
        log.debug('Pool recently refreshed. Not updating')
        return
    
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_pool.vpc.access_key)
    
    instances = EC2Instance.objects.filter(ec2_pool=ec2_pool).exclude(state='terminated')
    #TODO: get list of instance ids
    
    instance_ids = [instance.instance_id for instance in instances]
    
    instance_status_list = ec2_connection.get_all_instance_status(instance_ids)
    log.debug('Refreshing pool %s status' % ec2_pool.name)
    for status in instance_status_list:
        #assert isinstance(status, )
        log.debug('Refreshing instance %s' % status.id)
        try:
            id=status.id
            ec2_instance = instances.get(instance_id=id)
            if ec2_instance.state!=status.state_name:
                ec2_instance.state=status.state_name
                ec2_instance.save()
                instance=ec2_instance.get_instance()
                ec2_instance.state_transition_reason=instance.state_reason
                
            ec2_instance.instance_status = status.instance_status.status
            ec2_instance.system_status = status.system_status.status
            ec2_instance.save()
                
        except Exception, e:
            log.exception(e)
    ec2_pool.last_update_time = utcnow()
    ec2_pool.save()
    #for instance_status in instance_status_list: 
    #id = instance_status.id; state=state_name,
    #if state has changed - get instance.state_reason
    

def create_key_pair(pool):
    """Create a keypair and store it in the users storage directory
    """
    
    assert isinstance(pool, models.EC2Pool)
    vpc_connection, ec2_connection = aws_tools.create_connections(pool.vpc.access_key)
    name =  'keypair_%s' % pool.uuid
    key = ec2_connection.create_key_pair(name)
    
    #The directory where we store the ssh keypairs. Must be writable
    filepath = settings.KEYPAIR_FILEPATH
    
    path=os.path.join(filepath, name + '.pem')
    key.save(filepath)
    
    key_pair = EC2KeyPair(name=name, path=path)
    
    key_pair.save()
    return key_pair

def launch_pool(ec2_pool):
    """
    Launch a EC2 pool with the definitions provided by the ec2_pool object
    """
    
    log.debug('Launcing EC2 pool')
    assert isinstance(ec2_pool, EC2Pool)
    
    #Initiate the connection    
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_pool.vpc.access_key)
    
    log.debug('Retrieving machine image')
    ami = get_active_ami(ec2_connection)
    
    #Launch the master instance
    #Add the pool details to the launch string
    master_launch_string = ec2_config.MASTER_LAUNCH_STRING % (settings.HOST,
                                                              ec2_pool.uuid,
                                                              ec2_pool.secret_key,
                                                              ec2_pool.vpc.access_key.access_key_id,
                                                              ec2_pool.vpc.access_key.secret_key,
                                                              settings.EC2_LOG_LEVEL,
                                                              settings.EC2_POLL_TIME,
                                                              )
    #And launch
    log.debug('Launching Master node')
    master_reservation = ec2_connection.run_instances(ami.id,
                                               key_name=ec2_pool.key_pair.name,
                                               instance_type=settings.MASTER_NODE_TYPE,
                                               subnet_id=ec2_pool.vpc.subnet_id,
                                               security_group_ids=[ec2_pool.vpc.master_group_id],
                                               user_data=master_launch_string,
                                               min_count=1,#Only 1 instance needed
                                               max_count=1,
                                               )
    #
    sleep(2)
    
    ec2_instances = []

    master_instance = master_reservation.instances[0]
    master_ec2_instance = EC2Instance()
    master_ec2_instance.ec2_pool = ec2_pool
    master_ec2_instance.instance_id = master_instance.id
    master_ec2_instance.instance_type = ec2_pool.initial_instance_type
    master_ec2_instance.instance_role = 'master'
    
    
    master_ec2_instance.save()
    ec2_instances.append(master_ec2_instance)

    ec2_pool.master = master_ec2_instance
    
    ec2_pool.last_update_time = utcnow()
    ec2_pool.save()
    
    #wait until the master has a private ip address
    #sleep in beween
    log.debug('Waiting for private IP to be assigned to master node')
    sleep_time=5
    max_retrys=20
    current_try=0
    while master_ec2_instance.get_private_ip() == None and current_try<max_retrys:
        sleep(sleep_time)
        current_try+=1
    sleep(2)
    if ec2_pool.size > 0:
        log.debug('Launching worker nodes')
        worker_reservation = ec2_connection.run_instances(ami.id,
                                                   key_name=ec2_pool.key_pair.name,
                                                   instance_type=ec2_pool.initial_instance_type,
                                                   subnet_id=ec2_pool.vpc.subnet_id,
                                                   security_group_ids=[ec2_pool.vpc.worker_group_id],
                                                   user_data=ec2_config.WORKER_LAUNCH_STRING % ec2_pool.master.get_private_ip(),
                                                   min_count=ec2_pool.size,
                                                   max_count=ec2_pool.size,
                                                   )
        sleep(3)
        instances = worker_reservation.instances
        for instance in instances:
            ec2_instance = EC2Instance()
            ec2_instance.ec2_pool = ec2_pool
            ec2_instance.instance_id = instance.id
            ec2_instance.instance_type = ec2_pool.initial_instance_type
            ec2_instance.instance_role = 'worker'
            
            ec2_instance.save()
            
            ec2_instances.append(ec2_instance)
        
    #Create an sqs queue
    log.debug('Creating SQS for pool')
    sqs_connection = aws_tools.create_sqs_connection(ec2_pool.vpc.access_key)
    queue = sqs_connection.get_queue(ec2_pool.get_queue_name())
    if queue != None:
        sqs_connection.delete_queue(queue)
    
    sqs_connection.create_queue(ec2_pool.get_queue_name())
    
    #Create an SNS topic for instance alarm notifications
    log.debug('Creating SNS topic for alarms')
    sns_connection = aws_tools.create_sns_connection(ec2_pool.vpc.access_key)
    topic_data = sns_connection.create_topic(ec2_pool.get_alarm_notify_topic())
    
    topic_arn = topic_data['CreateTopicResponse']['CreateTopicResult']['TopicArn']
    
    log.debug('SNS topic created with arn %s' %topic_arn)
    
    ec2_pool.alarm_notify_topic_arn = topic_arn
    #And create a  subscription to the api_terminate_instance_alarm endpoint
    termination_notify_url = 'http://' + settings.HOST + str(reverse_lazy('api_terminate_instance_alarm'))
    
    sns_connection.subscribe(topic_arn, 'http', termination_notify_url)
    
    #Apply an alarm to each of the ec2 instances to notify that they should be shutdown should they be unused
    ##Note, this is now performed when the master node sends a notification back to the server through the API
    
    #Assign an elastic IP to the master instance
    #Try up to 5 times
    log.debug('Assigning elastic IP to master node')
    try:
        elastic_ip = assign_ip_address(master_ec2_instance)
        log.debug('Assigned elastic IP address to instance %s' % master_ec2_instance.instance_id)
    except Exception, e:
        log.error('Error assigning elastic ip to master instance %s' % master_ec2_instance.instance_id)
        log.exception(e)
        raise e
    
    ec2_pool.address = 'ubuntu@' + str(elastic_ip.public_ip)
    
    
    #Check to see if we can ssh in
    #Try a couple of times
    tries = 15
    for i in range(tries):
        log.debug('Testing SSH credentials')
        command = ['ssh', '-o', 'StrictHostKeyChecking=no', '-i', ec2_pool.key_pair.path, ec2_pool.address, 'pwd']
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={'DISPLAY' : ''})
        output = process.communicate()
        
        log.debug('SSH response:')
        log.debug(output)
        
        if process.returncode == 0:
            log.debug('SSH success')
            break
        sleep(5)
    
    
    return ec2_instances

def scale_up(ec2_pool, extra_nodes):
    log.debug('Scaling condor pool %s with %d extra nodes'%(ec2_pool.id, extra_nodes))
    return

def terminate_instances(instances):
    """Terminate the selected instances. Will also involve terminating any associated alarms and spot requests
    
    instances: iterable EC2Instances, list or queryset
    """
    vpc_connection, ec2_connection = aws_tools.create_connections(instances[0].ec2_pool.vpc.access_key)
    
    instance_ids = [instance.instance_id for instance in instances]
    
    log.debug('Terminating instances')
    
    #TODO: terminate the necessary alarms and spot requests before terminating the instances themselves.
    
    ec2_connection.terminate_instances(instance_ids)
    

def terminate_pool(ec2_pool):
    assert isinstance(ec2_pool, EC2Pool)
    log.debug('Terminating condor pool %s (user %s)' %(ec2_pool.name, ec2_pool.vpc.access_key.user.username))

    #Keep a track of the following errors
    errors=[]
    #First, create an ec2_connection object
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_pool.vpc.access_key)
    assert isinstance(ec2_connection, EC2Connection)
    instances = EC2Instance.objects.filter(ec2_pool=ec2_pool)
    
    
    #Dissassociate the IP address of the master instance and release i
    try:
        release_ip_address_from_instance(ec2_pool.master)
    except Exception, e:
        log.exception(e)
        errors.append(e)
        
    try:
        terminate_instances(instances)
    except Exception, e:
        log.exception(e)
        errors.append(e)

    key_pair = ec2_pool.key_pair
    
    try:
        ec2_connection.delete_key_pair(key_pair.name)
    except Exception, e:
        log.exception(e)
        errors.append(e)
    log.debug('Removing keypair file')
    try:
        os.remove(key_pair.path)
    except Exception, e:
        log.exception(e)
        pass
    ec2_pool.delete()
    key_pair.delete()

    
    try:
        log.debug('Deleting SQS queue for pool')
        sqs_connection = aws_tools.create_sqs_connection(ec2_pool.vpc.access_key)
        queue = sqs_connection.get_queue(ec2_pool.get_queue_name())
        if queue != None:
            sqs_connection.delete_queue(queue)
    except Exception, e:
        log.exception(e)

    log.debug('Pool terminated')
    return errors

def assign_ip_address(ec2_instance):
    """Assign a public IP address to the ec2 instance
    """
    #Check to see if there are any unassigned IP addresses:    
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_instance.ec2_pool.vpc.access_key)
    sleep(2)
    assert isinstance(ec2_instance, EC2Instance)
    ips = ElasticIP.objects.filter(vpc=ec2_instance.ec2_pool.vpc).filter(instance=None)
    
    if ips.count() > 0:
        #Use the first IP address
        log.debug('Using existing IP address')
        elastic_ip=ips[0]
    else:
        #We need to allocate a new ip address first
        log.debug('Allocating new IP address')
        address=ec2_connection.allocate_address('vpc')
        
        elastic_ip = ElasticIP()
        elastic_ip.allocation_id = address.allocation_id
        elastic_ip.public_ip = address.public_ip
        elastic_ip.vpc = ec2_instance.ec2_pool.vpc
    
    #Wait until the instance is in state running, then associate the ip address
    #Sleep 5 seconds between attempts
    #Max 6 attemps...
    sleep_time=5
    max_attempts=20
    attempt_count=0
    log.debug('Associating IP addresss with EC2 instance')
    while attempt_count < max_attempts:
        if ec2_instance.get_state() == 'running':
            log.debug('Instance running')
            sleep(sleep_time) #sleep again, just to be on the safe side
            break
        else:
            log.warning('Instance not running. Sleeping...')
            sleep(sleep_time)
            attempt_count +=1
    
    try:
    
        assert ec2_connection.associate_address(instance_id=ec2_instance.instance_id, allocation_id=elastic_ip.allocation_id)
        log.debug('IP associated with instance')
        elastic_ip.instance=ec2_instance
        
        #Use an inelegent workaround to get the association id of the address, since the api doesn't tell us this
        #Reload the address object
        new_address = ec2_connection.get_all_addresses(allocation_ids=[elastic_ip.allocation_id])[0]
        
        elastic_ip.association_id=new_address.association_id
        
        elastic_ip.save()
    
            
        return elastic_ip

    except Exception, e:
        log.debug('Unable to associate IP address with instance')
        raise e

def release_ip_address(key, allocation_id, association_id=None, public_ip=None):
    """Dissociate and release the IP address with the allocation id and optional association id. Alternatively just use public ip
    """
    
    vpc_connection, ec2_connection = aws_tools.create_connections(key)
    
    try:
        if association_id:
            log.debug('Disassociating IP')
            ec2_connection.disassociate_address(association_id=association_id)
        if public_ip:
            log.debug('Disassociating IP')
            ec2_connection.disassociate_address(public_ip=public_ip)
    except Exception, e:
        log.exception(e)
        
    try:
        log.debug('Releasing IP')
        if allocation_id:
            ec2_connection.release_address(allocation_id=allocation_id)
        else:
            ec2_connection.release_address(public_ip=public_ip)
    except Exception, e:
        log.exception(e)


def release_ip_address_from_instance(ec2_instance):
    """Dissassociate and release the public IP address of the ec2 instance
    """
    assert isinstance(ec2_instance, EC2Instance)
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_instance.ec2_pool.vpc.access_key)
    
    errors=[]
    try:
        ip = ElasticIP.objects.get(instance=ec2_instance)
        log.debug('Disassociating IP')
        ec2_connection.disassociate_address(association_id=ip.association_id)
    except Exception, e:
        log.exception(e)
        errors.append(e)
     
    try:
        log.debug('Releasing IP')
        ec2_connection.release_address(allocation_id=ip.allocation_id)
    except Exception, e:
        log.exception(e)
        errors.append(e)
    try:
        ip.delete()
    except Exception, e:
        log.exception(e)
        errors.append(e)
    
    return errors

def add_instance_alarm(instance):
    """Add a termination alarm to an EC2 instance. Alarm parameters are taken from ec2_config. Assumes that there is no alarm already present.
    """
    
    assert isinstance(instance, EC2Instance)
    #Only go forward if a termination alarm hasn't already been set
    if not instance.termination_alarm:
        
        log.debug('Adding termination alarm for instance %s' %instance.instance_id)
        
        connection = aws_tools.create_cloudwatch_connection(instance.ec2_pool.vpc.access_key)
        
        #Get the appropriate metric for creating the alarm
        
        metrics = connection.list_metrics(dimensions={'InstanceId': instance.instance_id}, metric_name='CPUUtilization')
        if len(metrics) == 0:
            log.debug('Metric not found yet, try again later')
            return
        #else continue
        assert len(metrics) == 1
        log.debug('Metric found')
        metric = metrics[0]
        
        #Create alarm for this metric
        
        alarm_name = 'cpu_termination_alarm_%s' % instance.instance_id
        
        log.debug('Adding termination alarm for instance %s'%instance.instance_id)
        
        alarm = metric.create_alarm(name=alarm_name,
                            comparison='<=',
                            threshold=ec2_config.DOWNSCALE_CPU_THRESHOLD,
                            period=ec2_config.DONWSCALE_CPU_PERIOD,
                            evaluation_periods=ec2_config.DOWNSCALE_CPU_EVALUATION_PERIODS,
                            statistic='Average',
                            alarm_actions=[instance.ec2_pool.alarm_notify_topic_arn],
                            )
        instance.termination_alarm = alarm_name
        assert isinstance(alarm, cloudwatch.MetricAlarm)
        instance.save()
        
    else:
        log.debug('Existing alarm already applied for instance %s' %instance.termination_alarm)
    
def add_instances_alarms(ec2_pool, include_master=False):
    """Apply instance alarms to all instances in the pool. By default, will not apply to master node
    """
    
    assert isinstance(ec2_pool, EC2Pool)
    
    if ec2_pool.auto_terminate:
        task_count = Task.objects.filter(ec2_pool=ec2_pool).count()
        if task_count > 0:
            
            instances = EC2Instance.objects.filter(ec2_pool=ec2_pool)
            
            for instance in instances:
                #Don't terminate the Master node!
                if instance != ec2_pool.master or include_master:
                    add_instance_alarm(instance)
        else:
            log.debug('Not adding alarm yet - no task submitted')