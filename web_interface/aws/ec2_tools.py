#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
#from boto.vpc import VPCConnection
#from boto.ec2 import EC2Connection, cloudwatch
#from boto.ec2.instance import Instance
from web_interface import models
from web_interface.aws import aws_tools, ec2_config
from web_interface.models import EC2Instance, VPC, EC2KeyPair, EC2Pool, ElasticIP, Task,\
    SpotRequest
import sys, os
#from exceptions import Exception
#from . import exceptions as Exception
from time import sleep
from cloud_copasi import settings
#from boto import sqs
import logging
import datetime
from django.utils.timezone import now as utcnow, now
from django.utils.timezone import utc
from django.urls import reverse_lazy
import subprocess
from boto.exception import BotoServerError, EC2ResponseError
import botocore
import spur

log = logging.getLogger(__name__)
slog = logging.getLogger('special')

def get_active_ami(ec2_connection):
    # assert isinstance(ec2_connection, EC2Connection)
    return ec2_connection.describe_images(ImageIds=[ec2_config.AMI_IMAGE_ID])['Images'][0]

def refresh_pool(ec2_pool):
    """Refresh the state of each instance in a ec2 pool
    """
    slog.debug('Refreshing pool %s status' % ec2_pool.name)

    if ec2_pool.copy_of:
        copied_pool = ec2_pool
        ec2_pool = EC2Pool.objects.get(id=ec2_pool.copy_of.id)
    else:
        copied_pool = None
    #If this pool is not an original, then don't refresh.

    slog.debug('refreshing status of pool %s' % ec2_pool.name)
    difference = utcnow() - ec2_pool.last_update_time.replace(tzinfo=utc)
    slog.debug('Time difference %s' % str(difference))
    if difference < datetime.timedelta(seconds=3):
        slog.debug('Pool recently refreshed. Not updating')
        return

    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_pool.vpc.access_key)

    #Get a list of any spot requests associated with the pool

    spot_requests = SpotRequest.objects.filter(ec2_pool=ec2_pool) | SpotRequest.objects.filter(ec2_pool__copy_of=ec2_pool)

    spot_request_ids = [request.request_id for request in spot_requests]

    try:
        if spot_request_ids != []:
            spot_request_list = ec2_connection.describe_spot_instance_requests(SpotInstanceRequestIds=[spot_request_ids])["SpotInstanceRequests"]
        else:
            spot_request_list = []
    except EC2ResponseError:
        #Perhaps a particular spot request wasn't found? Go through the list the slow way
        spot_request_list = []
        not_found_requests = []
        for spot_request_id in spot_request_ids:
            try:
                spot_instance_request = ec2_connection.describe_spot_instance_requests(SpotInstanceRequestIds=[spot_request_id])
                spot_request_list.append(spot_instance_request["SpotInstanceRequests"][0])
            except:
                slog.debug('Spot request %s not found, not updating status' %spot_request_id)
                not_found_requests.append(spot_request_id)
            #Don't do anything with spot requests that weren't found for now

    for request in spot_request_list:
        try:
            spot_request = SpotRequest.objects.get(request_id=request["SpotInstanceRequestId"])
            spot_request.status_code = request["Status"]["Code"]
            spot_request.status_message = request["Status"]["Message"]
            spot_request.state = request["State"]

            if request.instance_id != None:
                try:
                    ec2_instance = EC2Instance.objects.get(instance_id=request.instance_id)
                except:
                    ec2_instance = EC2Instance(ec2_pool=ec2_pool,
                                               instance_type=spot_request.instance_type,
                                               instance_role='worker',
                                               instance_id=request["InstanceId"],
                                               state='unknown',
                                               instance_status='unknown',
                                               system_status='unknown',
                                               )
                    ec2_instance.save()
                spot_request.ec2_instance = ec2_instance

            else:
                spot_request.ec2_instance = None

            spot_request.save()
        except Exception as  e:
            slog.exception(e)

    instances = EC2Instance.objects.filter(ec2_pool=ec2_pool) | EC2Instance.objects.filter(ec2_pool__copy_of=ec2_pool)

    instances = instances.exclude(state='terminated')

    instance_ids = [instance.instance_id for instance in instances]

    try:
        instance_status_list = ec2_connection.describe_instance_status(InstanceIds=instance_ids)["InstanceStatuses"]
    except EC2ResponseError:
        #Perhaps an instance wasn't found? If so we'll have to go through the list the slow way
        instance_status_list = []
        not_found_instances = []
        for instance_id in instance_ids:
            try:
                instance_status = ec2_connection.describe_instance_status(InstanceIds=[instance_id])["InstanceStatuses"][0]
                instance_status_list.append(instance_status)
            except:
                slog.debug('Instance %s not found, presuming terminated' % instance_id)
                not_found_instances.append(instance_id)

        for instance_id in not_found_instances:
            ec2_instance = EC2Instance.objects.get(instance_id=instance_id)
            ec2_instance.state='terminated'
            ec2_instance.instance_status = 'terminated'
            ec2_instance.system_status = 'terminated'
            ec2_instance.state_transition_reason = 'Unknown'

            ec2_instance.save()


    for status in instance_status_list:
        #assert isinstance(status, )
        slog.debug('Refreshing instance %s' % status["InstanceId"])
        try:
            id=status["InstanceId"]
            ec2_instance = instances.get(instance_id=id)
            if ec2_instance.state!=status["InstanceState"]["Name"]:
                ec2_instance.state=status["InstanceState"]["Name"]
                ec2_instance.save()
                instance=ec2_instance.get_instance()
                ec2_instance.state_transition_reason=instance.state_reason

            ec2_instance.instance_status = status["InstanceStatus"]["Status"]
            ec2_instance.system_status = status["SystemStatus"]["Status"]
            ec2_instance.save()
        except Exception as  e:
            slog.exception(e)

    #Add instance termination alarms. Because instance metrics don't appear instantly,
    #We have to do this now, as opposed to when the pool was first launched
    #If instance alarms have already been added, this step will be quickly skipped
    if ec2_pool.smart_terminate:
        add_instances_alarms(ec2_pool)

    ec2_pool.last_update_time = now()
    ec2_pool.save()

    #Did we just update the status of a copied pool?
    if copied_pool:
        copied_pool.last_update_time = ec2_pool.last_update_time
        copied_pool.save()



def create_key_pair(pool):
    """Create a keypair and store it in the users storage directory
    """

    assert isinstance(pool, models.EC2Pool)
    vpc_connection, ec2_connection = aws_tools.create_connections(pool.vpc.access_key)
    name =  'keypair_%s' % pool.uuid
    key = ec2_connection.create_key_pair(KeyName=name)

    #The directory where we store the ssh keypairs. Must be writable
    filepath = settings.KEYPAIR_FILEPATH

    path=os.path.join(filepath, name + '.pem')
    slog.debug(str(key))
    #key.save(filepath)
    with open(path, 'w') as file:
        file.write(key['KeyMaterial'])

    key_pair = EC2KeyPair(name=name, path=path)

    key_pair.save()
    return key_pair

def launch_pool(ec2_pool):
    """
    Launch a EC2 pool with the definitions provided by the ec2_pool object
    """

    slog.debug('Launcing EC2 pool')
    assert isinstance(ec2_pool, EC2Pool)

    errors = []

    #Initiate the connection
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_pool.vpc.access_key)

    log.debug('Retrieving machine image')
    ami = get_active_ami(ec2_connection)
    slog.debug("AMI Obtained")
    #Launch the master instance
    #Add the pool details to the launch string
    #master_launch_string = ec2_config.MASTER_LAUNCH_STRING
    #And launch
    slog.debug('Launching Master node')
    try:
        master_reservation = ec2_connection.run_instances(ImageId=ami['ImageId'],
                                                   KeyName=ec2_pool.key_pair.name,
                                                   InstanceType=settings.MASTER_NODE_TYPE,
                                                   SubnetId=ec2_pool.vpc.subnet_id,
                                                   SecurityGroupIds=[ec2_pool.vpc.master_group_id],
                                                   MinCount=1,#Only 1 instance needed
                                                   MaxCount=1,
                                                   )
    except botocore.exceptions.ClientError as error:
        slog.debug(error)
        
    #
    sleep(2)
    slog.debug("Master reserved")

    ec2_instances = []

    master_instance = master_reservation['Instances'][0]
    slog.debug(master_instance)
    master_ec2_instance = EC2Instance()
    master_ec2_instance.ec2_pool = ec2_pool
    master_ec2_instance.instance_id = master_instance['InstanceId']
    master_ec2_instance.instance_type = settings.MASTER_NODE_TYPE
    master_ec2_instance.instance_role = 'master'


    master_ec2_instance.save()
    ec2_instances.append(master_ec2_instance)

    ec2_pool.master = master_ec2_instance
    
    #wait until the master has a private ip address
    #sleep in beween
    log.debug('Waiting for private IP to be assigned to master node')
    slog.debug('Waiting for private IP to be assigned to master node')
    sleep_time=5
    max_retrys=20
    current_try=0
    while master_ec2_instance.get_private_ip() == None and current_try<max_retrys:
        sleep(sleep_time)
        current_try+=1
    sleep(2)
    slog.debug("IPs assigned")
    slog.debug('Launching Submit node')
    try:
        submit_reservation = ec2_connection.run_instances(ImageId=ami['ImageId'],
                                                   KeyName=ec2_pool.key_pair.name,
                                                   InstanceType=settings.MASTER_NODE_TYPE,
                                                   SubnetId=ec2_pool.vpc.subnet_id,
                                                   SecurityGroupIds=[ec2_pool.vpc.master_group_id],
                                                   MinCount=1,#Only 1 instance needed
                                                   MaxCount=1,
                                                   )
    except botocore.exceptions.ClientError as error:
        slog.debug(error)

    #
    sleep(2)
    slog.debug("Submit reserved")

    ec2_instances = []

    submit_instance = submit_reservation['Instances'][0]
    slog.debug(submit_instance)
    submit_ec2_instance = EC2Instance()
    submit_ec2_instance.ec2_pool = ec2_pool
    submit_ec2_instance.instance_id = submit_instance['InstanceId']
    submit_ec2_instance.instance_type = settings.MASTER_NODE_TYPE
    submit_ec2_instance.instance_role = 'submit'


    submit_ec2_instance.save()
    ec2_instances.append(submit_ec2_instance)

    ec2_pool.submit = submit_ec2_instance
    # line below being problematic
    ec2_pool.last_update_time = now()
    ec2_pool.save()

    #wait until the master has a private ip address
    #sleep in beween
    log.debug('Waiting for private IP to be assigned to submit node')
    slog.debug('Waiting for private IP to be assigned to submit node')
    sleep_time=5
    max_retrys=20
    current_try=0
    while submit_ec2_instance.get_private_ip() == None and current_try<max_retrys:
        sleep(sleep_time)    
        current_try+=1
    sleep(2)
    slog.debug("IPs assigned")



    if ec2_pool.size > 0:
        slog.debug('Launching worker nodes')

        #Are we launcing fixed price or spot instances?
        try:
            if not ec2_pool.spot_request:
                #Fix price launch. This is easy.
                worker_reservation = ec2_connection.run_instances(ImageId=ami['ImageId'],
                                                           KeyName=ec2_pool.key_pair.name,
                                                           InstanceType=ec2_pool.initial_instance_type,
                                                           SubnetId=ec2_pool.vpc.subnet_id,
                                                           SecurityGroupIds=[ec2_pool.vpc.worker_group_id],
                                                           MinCount=ec2_pool.size,
                                                           MaxCount=ec2_pool.size,
                                                           )
                sleep(3)
                slog.debug("Worker nodes created") 
                instances = worker_reservation['Instances']
                for instance in instances:
                    ec2_instance = EC2Instance()
                    ec2_instance.ec2_pool = ec2_pool
                    ec2_instance.instance_id = instance['InstanceId']
                    ec2_instance.instance_type = ec2_pool.initial_instance_type
                    ec2_instance.instance_role = 'worker'

                    ec2_instance.save()

                    ec2_instances.append(ec2_instance)
                slog.debug("worker nodes saved into DB")

            else:
                #We're launching a spot request pool instead.
                worker_requests = ec2_connection.request_spot_instances(SpotPrice=str(ec2_pool.spot_price),
                                                                        ImageId=ami['ImageId'],
                                                                        Type='persistent',
                                                                        InstanceCount=ec2_pool.size,
                                                                        KeyName=ec2_pool.key_pair.name,
                                                                        InstanceType=ec2_pool.initial_instance_type,
                                                                        SubnetId=ec2_pool.vpc.subnet_id,
                                                                        SecurityGroupIds=[ec2_pool.vpc.worker_group_id],
                                                                        )["SpotInstanceRequests"]
                for request in worker_requests:
                    spot_request = SpotRequest(ec2_pool=ec2_pool,
                                               request_id=request['SpotRequestId'],
                                               price=request['SpotPrice'],
                                               status_code=request['Status']['Code'],
                                               status_message=request['Status']['Message'],
                                               state=request['State'],
                                               instance_type=ec2_pool.initial_instance_type,
                                               )
                    spot_request.save()

        except EC2ResponseError as e:
            errors.append(('Error launching worker instances', 'An error occured when launching the worker instances, \
            however a master instance was launched successfully. Check your AWS usage limit to ensure you \
            are not trying to exceed it. You should either try again to scale the pool up, or terminate it.'))
            errors.append(e)
    os.chmod(ec2_pool.key_pair.path, 0o400)
    slog.debug("permission altering attempted")
    #Create an sqs queue
    slog.debug('Creating SQS for pool')
    sqs_connection = aws_tools.create_sqs_connection(ec2_pool.vpc.access_key)
    slog.debug('SQS created')
    try:
        queue = sqs_connection.get_queue_url(QueueName=ec2_pool.get_queue_name())
        slog.debug("queue_url " + queue)
        if queue != None:
            sqs_connection.delete_queue(QueueUrl=queue)
    except Exception as e:
        slog.debug("creating the queue")
        sqs_connection.create_queue(QueueName=ec2_pool.get_queue_name())
        slog.debug("queue created")

    #Create an SNS topic for instance alarm notifications
    slog.debug('Creating SNS topic for alarms')
    sns_connection = aws_tools.create_sns_connection(ec2_pool.vpc.access_key)
    topic_data = sns_connection.create_topic(Name=ec2_pool.get_alarm_notify_topic())

    topic_arn = topic_data['TopicArn']

    slog.debug('SNS topic created with arn %s' %topic_arn)

    ec2_pool.alarm_notify_topic_arn = topic_arn
    #And create a  subscription to the api_terminate_instance_alarm endpoint
    termination_notify_url = 'http://' + settings.HOST + str(reverse_lazy('api_terminate_instance_alarm'))
    slog.debug("termination url: " + termination_notify_url)
    try:
        sns_connection.subscribe(TopicArn=topic_arn, Protocol='http', Endpoint=termination_notify_url)
    except Exception as e:
        slog.debug(e)
        errors.append(('Error enabling smart termination', 'Smart termination was not successfully enabled'))
        try:
            ec2_pool.smart_terminate = False
            sns_connection.delete_topic(TopicArn=topic_arn)
        except:
            pass
    #Apply an alarm to each of the ec2 instances to notify that they should be shutdown should they be unused
    ##Note, this is now performed when the master node sends a notification back to the server through the API

    #Assign an elastic IP to the master instance
    #Try up to 5 times
    slog.debug('Assigning elastic IP to master node')
    try:
        elastic_ip_master = assign_ip_address(master_ec2_instance)
        slog.debug('Assigned elastic IP address to master instance %s' % master_ec2_instance.instance_id )
        sleep(10)
        shell = spur.SshShell(hostname=elastic_ip_master.public_ip, username="ubuntu", private_key_file=ec2_pool.key_pair.path, missing_host_key=spur.ssh.MissingHostKey.accept)
        result = shell.run(['sh', '-c', 'curl -fsSL https://get.htcondor.org | sudo GET_HTCONDOR_PASSWORD="password" /bin/bash -s -- --no-dry-run --central-manager '+elastic_ip_master.public_ip])
        slog.debug(result)
    except Exception as  e:
        slog.error('Error assigning elastic ip to master instance %s' % master_ec2_instance.instance_id)
        slog.exception(str(e))
        raise e
    slog.debug('Assigning elastic IP to submit node')
    try:
        elastic_ip_submit = assign_ip_address(submit_ec2_instance)
        slog.debug('Assigned elastic IP address to submit instance %s' % submit_ec2_instance.instance_id)
        sleep(10)
        shell = spur.SshShell(hostname=elastic_ip_submit.public_ip, username="ubuntu", private_key_file=ec2_pool.key_pair.path, missing_host_key=spur.ssh.MissingHostKey.accept)
        result = shell.run(['sh', '-c', 'curl -fsSL https://get.htcondor.org | sudo GET_HTCONDOR_PASSWORD="password" /bin/bash -s -- --no-dry-run --submit '+elastic_ip_master.public_ip])
        slog.debug(result)
        ec2_pool.address = 'ubuntu@' + str(elastic_ip_submit.public_ip)
    except Exception as  e:
        slog.error('Error assigning elastic ip to submit instance %s' % submit_ec2_instance.instance_id)
        slog.exception(str(e))
        raise e
    for ins in ec2_instances:
        sleep(3)
        if ins.instance_role=='worker':
            try:
                elastic_ip_worker = assign_ip_address(ins)
                slog.debug('Assigned elastic IP address to worker instance %s' % ins.instance_id)
                sleep(10)
                shell = spur.SshShell(hostname=elastic_ip_worker.public_ip, username="ubuntu", private_key_file=ec2_pool.key_pair.path, missing_host_key=spur.ssh.MissingHostKey.accept)
                result = shell.run(['sh', '-c', 'curl -fsSL https://get.htcondor.org | sudo GET_HTCONDOR_PASSWORD="password" /bin/bash -s -- --no-dry-run --execute '+elastic_ip_master.public_ip])
                slog.debug(result)
            except Exception as  e:
                slog.error('Error assigning elastic ip to worker instance %s' % ins.instance_id)
                slog.exception(e)
                raise e

    #Check to see if we can ssh in
    #Try a couple of times
    tries = 15
    for i in range(tries):
        slog.debug('Testing SSH credentials')
        command = ['ssh', '-o', 'StrictHostKeyChecking=no', '-i', ec2_pool.key_pair.path, ec2_pool.address, 'pwd']

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={'DISPLAY' : ''})
        output = process.communicate()

        slog.debug('SSH response:')
        slog.debug(output)

        if process.returncode == 0:
            slog.debug('SSH success')
            break
        sleep(5)

    slog.debug("Printing errors and exiting the function")
    slog.debug(str(errors))
    return errors

def scale_up(ec2_pool, extra_nodes, instance_type, spot, spot_bid_price):
    log.debug('Scaling condor pool %s with %d extra nodes'%(ec2_pool.id, extra_nodes))

    errors = []
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_pool.vpc.access_key)

    log.debug('Retrieving machine image')
    ami = get_active_ami(ec2_connection)

    try:
        if not spot:
            #Fix price launch. This is easy.
            log.debug('Launching fixed price instances')
            worker_reservation = ec2_connection.run_instances(ImageId=ami["ImageId"],
                                                       KeyName=ec2_pool.key_pair.name,
                                                       InstanceType=instance_type,
                                                       SubnetId=ec2_pool.vpc.subnet_id,
                                                       SecurityGroupIds=[ec2_pool.vpc.worker_group_id],
                                                       UserData=ec2_config.WORKER_LAUNCH_STRING % ec2_pool.master.get_private_ip(),
                                                       MinCount=extra_nodes,
                                                       MaxCount=extra_nodes,
                                                       )
            sleep(3)
            instances = worker_reservation["Instances"]
            for instance in instances:
                ec2_instance = EC2Instance()
                ec2_instance.ec2_pool = ec2_pool
                ec2_instance.instance_id = instance["InstanceId"]
                ec2_instance.instance_type = ec2_pool.initial_instance_type
                ec2_instance.instance_role = 'worker'

                ec2_instance.save()



        else:
            #We're launching a spot request pool instead.
            log.debug('Launching spot requests')
            worker_requests = ec2_connection.request_spot_instances(SpotPrice=str(spot_bid_price),
                                                                    Type='persistent',
                                                                    InstanceCount=extra_nodes,
                                                                    LaunchSpecification={"ImageId": ami["ImageId"], "KeyName": ec2_pool.key_pair.name, "InstanceType":instance_type, "UserData":ec2_config.WORKER_LAUNCH_STRING % ec2_pool.master.get_private_ip(), "SubnetId":ec2_pool.vpc.subnet_id, "SecurityGroupIds":[ec2_pool.vpc.worker_group_id]}
                                                                    )["SpotInstanceRequests"]
            for request in worker_requests:
                spot_request = SpotRequest(ec2_pool=ec2_pool,
                                           request_id=request['SpotInstanceRequestId'],
                                           price=request["SpotPrice"],
                                           status_code=request["Status"]["Code"],
                                           status_message=request["Status"]["Message"],
                                           state=request["State"],
                                           instance_type=ec2_pool.initial_instance_type,
                                           )
                spot_request.save()

    except EC2ResponseError as e:
        errors.append(('Error launching worker instances', 'An error occured when launching the worker instances, \
        however a master instance was launched successfully. Check your AWS usage limit to ensure you \
        are not trying to exceed it. You should either try again to scale the pool up, or terminate it.'))
        errors.append(e)



    return errors

def scale_down(ec2_pool, nodes_to_terminate, instance_type, pricing, spot_price_order, spot_price_custom):

    log.debug('Scaling pool %s down' % ec2_pool.name)
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_pool.vpc.access_key)
    errors=[]
    #Filter down instances so that they match the query

    instances = EC2Instance.objects.filter(ec2_pool=ec2_pool).exclude(instance_role='master')
    spot_requests = SpotRequest.objects.filter(ec2_pool=ec2_pool)

    if instance_type != None:
        instances = instances.filter(instance_type=instance_type)
        spot_requests = spot_requests.filter(instance_type=instance_type)
    if pricing == 'fixed':
        instances = instances.filter(spotrequest=None)
        spot_requests = spot_requests.none()
    else:
        instances = instances.exclude(spotrequest=None)

    if pricing == 'spot' and spot_price_order == 'custom':
        spot_requests = spot_requests.filter(price=spot_price_custom)
        instances = instances.filter(spotrequest__in=spot_requests)
    elif pricing == 'spot' and spot_price_order == 'lowest':
        spot_requests = spot_requests.order_by('price')
        instances = instances.order_by('spotrequest__price')
    elif pricing == 'spot' and spot_price_order == 'highest':
        spot_requests = spot_requests.order_by('-price')
        instances = instances.order_by('-spotrequest__price')


    #Now we have the list of instances to terminate, terminate them
    if nodes_to_terminate > instances.count():
        instances = instances
    else:
        instances = instances[0:nodes_to_terminate]

    if nodes_to_terminate > spot_requests.count():
        spot_requests = spot_requests
    else:
        spot_requests = spot_requests[0:nodes_to_terminate]

    if pricing == 'fixed':
        instances_to_terminate = [instance.instance_id for instance in instances]
    else:
        instances_to_terminate = []
        for spot_request in spot_requests:
            if spot_request.ec2_instance != None:
                instances_to_terminate.append(spot_request.ec2_instance.instance_id)

    #Are there any spot requests to terminate?
    try:
        spot_request_ids = [request.request_id for request in spot_requests]
        if spot_request_ids != []:
            log.debug('Cancelling %d spot requests'%len(spot_request_ids))
            ec2_connection.cancel_spot_instance_requests(SpotInstanceRequestIds=spot_request_ids)
            for spot_request in spot_requests:
                spot_request.delete()
        if instances_to_terminate != []:
            terminate_instances(instances)
    except Exception as  e:
        log.exception(e)
        errors.append(e)

def terminate_instances(instances):
    """Terminate the selected instances. Will also involve terminating any associated alarms and spot requests

    instances: iterable EC2Instances, list or queryset
    """
    vpc_connection, ec2_connection = aws_tools.create_connections(instances[0].ec2_pool.vpc.access_key)

    #Terminate any spot requests first
    spot_requests_to_terminate = SpotRequest.objects.filter(ec2_instance__in=instances)
    spot_request_ids = [request.request_id for request in spot_requests_to_terminate]
    try:
        if spot_request_ids != []:
            log.debug('Cancelling %d spot requests'%len(spot_request_ids))
            ec2_connection.cancel_spot_instance_requests(SpotInstanceRequestIds=spot_request_ids)
            for spot_request in spot_requests_to_terminate:
                spot_request.delete()
    except Exception as  e:
        log.exception(e)

    log.debug('Deleting termination alarms')
    for instance in instances:
        try:
            cloudwatch_connection = aws_tools.create_cloudwatch_connection(instance.ec2_pool.vpc.access_key)

            if instance.termination_alarm:
                cloudwatch_connection.delete_alarms(AlarmNames=[instance.termination_alarm])
        except Exception as  e:
            log.exception(e)


    instance_ids = [instance.instance_id for instance in instances]

    log.debug('Terminating instances')

    #TODO: terminate the necessary alarms and spot requests before terminating the instances themselves.

    ec2_connection.terminate_instances(InstanceIds=instance_ids)


def terminate_pool(ec2_pool):
    assert isinstance(ec2_pool, EC2Pool)
    log.debug('Terminating condor pool %s (user %s)' %(ec2_pool.name, ec2_pool.vpc.access_key.user.username))

    #Keep a track of the following errors
    errors=[]
    #Create an ec2_connection object
    vpc_connection, ec2_connection = aws_tools.create_connections(ec2_pool.vpc.access_key)

    #First, refresh the status of the pool
    try:
        refresh_pool(ec2_pool)
    except Exception as  e:
        log.exception(e)
        errors.append(e)

    spot_requests = SpotRequest.objects.filter(ec2_pool=ec2_pool)
    spot_request_ids = [request.request_id for request in spot_requests]

    try:
        log.debug('Cancelling %d spot requests'%len(spot_request_ids))
        if spot_request_ids != []:
            ec2_connection.cancel_spot_instance_requests(SpotInstanceRequestIds=spot_request_ids)
            for spot_request in spot_requests:
                spot_request.delete()
    except Exception as  e:
        log.exception(e)
        errors.append(e)



    instances = EC2Instance.objects.filter(ec2_pool=ec2_pool)
    instances = instances.exclude(state='terminated').exclude(state='shutting-down')

    #Dissassociate the IP address of the master instance and release i
    try:
        release_ip_address_from_instance(ec2_pool.master)
    except Exception as  e:
        log.exception(e)
        errors.append(e)

    try:
        terminate_instances(instances)
    except Exception as  e:
        log.exception(e)
        errors.append(e)

    key_pair = ec2_pool.key_pair

    try:
        ec2_connection.delete_key_pair(KeyName=key_pair.name)
    except Exception as  e:
        log.exception(e)
        errors.append(e)
    log.debug('Removing keypair file')
    try:
        os.remove(key_pair.path)
    except Exception as  e:
        log.exception(e)
        pass


    try:
        log.debug('Deleting SQS queue for pool')
        sqs_connection = aws_tools.create_sqs_connection(ec2_pool.vpc.access_key)
        queue = sqs_connection.get_queue_url(QueueName=ec2_pool.get_queue_name())
        if queue != None:
            sqs_connection.delete_queue(QueueUrl=queue)
    except Exception as  e:
        log.exception(e)
    try:
        log.debug('Deleting SQS topic')
        sns_connection = aws_tools.create_sns_connection(ec2_pool.vpc.access_key)
        sns_connection.delete_topic(Topic=ec2_pool.alarm_notify_topic_arn)
    except Exception as  e:
        log.exception(e)

    ec2_pool.delete()
    # added by fizza
    try:
        key_pair.delete()
    except Exception as ee:
        slog.debug(ee)

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
    slog.debug("Attempting to assign IP addresses")
    sleep_time=5
    allocate_new = False
    if ips.count() > 0:
        #Use the first IP address
        slog.debug('Using existing IP address')
        elastic_ip=ips[0]
        try:
            release_ip_address(ec2_instance.condor_pool.vpc.acess_key, allocation_id=elastic_ip.allocation_id, association_id=elastic_ip.association_id)
        except Exception as  e:
            slog.exception(e)
            allocate_new = True
    elif ips.count() == 0 or allocate_new:
        #We need to allocate a new ip address first
        slog.debug("need to allocate a new IP address")
        max_attempts=5
        attempt_count=0
        while attempt_count < max_attempts:
            try:
                log.debug('Allocating new IP address')
                address=ec2_connection.allocate_address(Domain='vpc')

                elastic_ip = ElasticIP()
                elastic_ip.allocation_id = address['AllocationId']
                elastic_ip.public_ip = address['PublicIp']
                elastic_ip.vpc = ec2_instance.ec2_pool.vpc
                slog.debug("IP allocated")
                assert elastic_ip.allocation_id != None
                assert elastic_ip.allocation_id != ''
                break
            except Exception as  e:
                #Something is wrong here with the elastic ip
                slog.exception(e)
                attempt_count += 1
                try:
                    elastic_ip.delete()
                except:
                    pass
                try:
                    ec2_connection.release_address(AllocationId=address.allocation_id)
                except:
                    pass
                sleep(sleep_time)

    #Wait until the instance is in state running, then associate the ip address
    #Sleep 5 seconds between attempts
    #Max 6 attemps...
    max_attempts=20
    attempt_count=0
    slog.debug('Associating IP addresss with EC2 instance')
    while attempt_count < max_attempts:
        if ec2_instance.get_state() == 'running':
            slog.debug('Instance running')
            sleep(sleep_time) #sleep again, just to be on the safe side
            break
        else:
            slog.warning('Instance not running. Sleeping...')
            sleep(sleep_time)
            attempt_count +=1
    slog.debug("Now try associating an elastic IP")
    #Now try associating an elastic IP
    max_attempts=5
    attempt_count=0
    while attempt_count < max_attempts:
        try:

            #assert ec2_connection.associate_address(InstanceId=ec2_instance.instance_id, AllocationId=elastic_ip.allocation_id)
            ec2_connection.associate_address(InstanceId=ec2_instance.instance_id, AllocationId=elastic_ip.allocation_id)
            sleep(sleep_time)
            slog.debug('IP associated with instance')
            elastic_ip.instance=ec2_instance

            #Use an inelegent workaround to get the association id of the address, since the api doesn't tell us this
            #Reload the address object
            new_address = ec2_connection.describe_addresses(AllocationIds=[elastic_ip.allocation_id])["Addresses"][0]

            elastic_ip.association_id=new_address['AssociationId']

            elastic_ip.save()


            return elastic_ip

        except Exception as  e:
            slog.debug('Unable to associate IP address with instance')
            slog.debug(e)
            attempt_count += 1
            if attempt_count == max_attempts: raise e
            sleep(sleep_time)

def release_ip_address(key, allocation_id, association_id=None, public_ip=None):
    """Dissociate and release the IP address with the allocation id and optional association id. Alternatively just use public ip
    """

    vpc_connection, ec2_connection = aws_tools.create_connections(key)

    try:
        if association_id:
            log.debug('Disassociating IP')
            ec2_connection.disassociate_address(AssociationId=association_id)
        if public_ip:
            log.debug('Disassociating IP')
            ec2_connection.disassociate_address(PublicIp=public_ip)
    except Exception as  e:
        log.exception(e)

    try:
        log.debug('Releasing IP')
        if allocation_id:
            ec2_connection.release_address(AllocationId=allocation_id)
        else:
            ec2_connection.release_address(PublicIp=public_ip)
    except Exception as  e:
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
        ec2_connection.disassociate_address(AssociationId=ip.association_id)
    except Exception as  e:
        log.exception(e)
        errors.append(e)

    try:
        log.debug('Releasing IP')
        ec2_connection.release_address(AllocationId=ip.allocation_id)
    except Exception as  e:
        log.exception(e)
        errors.append(e)
    try:
        ip.delete()
    except Exception as  e:
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

        metrics = connection.list_metrics(Dimensions={'InstanceId': instance.instance_id}, MetricName='CPUUtilization')["Metrics"]
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

        alarm = connection.set_metric_alarm(AlarmName=alarm_name,
                            ComparisonOperator='<=',
                            Threshold=ec2_config.DOWNSCALE_CPU_THRESHOLD,
                            Period=ec2_config.DONWSCALE_CPU_PERIOD,
                            EvaluationPeriods=ec2_config.DOWNSCALE_CPU_EVALUATION_PERIODS,
                            Statistic='Average',
                            AlarmActions=[instance.ec2_pool.alarm_notify_topic_arn],
                            )
        instance.termination_alarm = alarm_name
        #assert isinstance(alarm, cloudwatch.MetricAlarm)
        instance.save()

    else:
        pass#Instance alarm already applied. Do nothing

def add_instances_alarms(ec2_pool, include_master=False, instances=None):
    """Apply instance alarms to all instances in the pool. By default, will not apply to master node
    """

    assert isinstance(ec2_pool, EC2Pool)
    if instances == None:
        instances = EC2Instance.objects.filter(ec2_pool=ec2_pool)
    if not include_master:
        instances = instances.exclude(id=ec2_pool.master.id) #Don't terminate the Master node!

    for instance in instances:
        add_instance_alarm(instance)

def remove_instance_alarm(instance):
    """Remove the instance alarm from the ec2 instance
    """
    assert isinstance(instance, EC2Instance)
    if instance.termination_alarm:
        connection = aws_tools.create_cloudwatch_connection(instance.ec2_pool.vpc.access_key)
        try:
            connection.delete_alarms(AlarmNames=[instance.termination_alarm])
            instance.termination_alarm = None
            instance.save()
        except Exception as  e:
            log.exception(e)
            return e
    return None

def remove_instances_alarms(ec2_pool):
    assert isinstance(ec2_pool, EC2Pool)
    instances = EC2Instance.objects.filter(ec2_pool=ec2_pool).exclude(id=ec2_pool.master.id)
    errors = []
    for instance in instances:
        error = remove_instance_alarm(instance)
        if error:
            errors.append(error)
    if errors == []:
        ec2_pool.smart_terminate = False
        ec2_pool.save()
    return errors
