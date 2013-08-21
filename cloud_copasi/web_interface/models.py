#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from django.db import models
from django.contrib.auth.models import User
# Create your models here.
from django.core.validators import RegexValidator, MinValueValidator
from boto.s3.connection import S3Connection
from cloud_copasi.web_interface.aws import aws_tools, ec2_config, s3_tools
from boto.vpc import VPCConnection
from boto.ec2 import EC2Connection
import sys, os, random, string
from cloud_copasi import copasi
import cPickle
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from cloud_copasi.web_interface.fields import UUIDField
import json
import datetime


class Profile(models.Model):
    """Stores additional profile information for a user
    """
    user = models.OneToOneField(User)
    institution = models.CharField(max_length=50)
    


class AWSAccessKey(models.Model):
    """Represents an AWS access key
    """
    user = models.ForeignKey(User)
    
    name = models.CharField(max_length=100, help_text='For your convenience, assign a unique name to this access key', verbose_name='Key name')

    access_key_id = models.CharField(max_length=20, help_text='The 20-character AWS access key ID', verbose_name='Access key ID', validators=[RegexValidator(regex='^.{20}$', message='Length has to be 20', code='nomatch')])
    
    secret_key = models.CharField(max_length=40, help_text='The 40-character secret access key associated with the access key ID', verbose_name='Secret access key', validators=[RegexValidator(regex='^.{40}$', message='Length has to be 40', code='nomatch')])
    
    copy_of = models.ForeignKey('self', null=True, blank=True, verbose_name = 'Is this key a shared version of an original key?')
    
    def __unicode__(self):
        return "%s, %s, %s" % (self.name, self.access_key_id, self.user)
    
    class Meta:
        app_label = 'web_interface'
        unique_together = (('user', 'name'), ('user', 'access_key_id'))

class VPC(models.Model):
    """Represents an AWS VPC in which we can run jobs
    """
    access_key = models.OneToOneField(AWSAccessKey, null=True)
    #The VPC in which everything else resides
    vpc_id = models.CharField(max_length=20, verbose_name='VPC ID')
    
    subnet_id = models.CharField(max_length=20, verbose_name='Subnet ID')
    
    internet_gateway_id = models.CharField(max_length=20, verbose_name='Internet gateway ID')
    
    route_table_id =  models.CharField(max_length=20, verbose_name='Route table ID')
    
    route_table_association_id = models.CharField(max_length=20, verbose_name='Route table and subnet association ID')
    #Condor master security group
    master_group_id = models.CharField(max_length=20, verbose_name='Condor Master security group ID')
    #Condor worker security group
    worker_group_id = models.CharField(max_length=20, verbose_name='Condor Worker security group ID')
    
    s3_bucket_name = models.CharField(max_length=20, verbose_name = 'S3 bucket for storing ')
    
    class Meta:
        app_label = 'web_interface'
        
    def __unicode__(self):
        return "VPC %s (keypair %s)" % (self.vpc_id, self.access_key.name)
        
    def get_vpc(self, vpc_connection):
        """Returns the boto vpc object
        """
        return vpc_connection.get_all_vpcs([self.vpc_id])[0]
    
    def get_internet_gateway(self, vpc_connection):
        """Returns the boto internet gateway object
        """
        return vpc_connection.get_all_internet_gateways([self.internet_gateway_id])[0]
    
    def get_route_table(self, vpc_connection):
        """Returns the boto route table object
        """
        return vpc_connection.get_all_route_tables([self.route_table_id])[0]
    
    def get_master_group(self, ec2_connection):
        """Returns the boto Master security group object
        """
        return ec2_connection.get_all_security_groups(group_ids=[self.master_group_id])[0]
    def get_worker_group(self, ec2_connection):
        """Returns the boto Worker security group object
        """
        return ec2_connection.get_all_security_groups(group_ids=[self.worker_group_id])[0]
    
    def get_status(self):
        
        try:
            vpc_connection, ec2_connection = aws_tools.create_connections(self.access_key)
            
            vpc_state = self.get_vpc(vpc_connection).state
            
            vpc_connection.close()
            ec2_connection.close()
            return vpc_state
        except Exception, e:
            return 'error: ' + str(e)
    def get_keypair(self, ec2_connection):
        """
        Returns the EC2 keypair object
        """
        return ec2_connection.get_key_pair(self.key_pair_name)
    

def create_secret_key():
        length=30
        return "".join([random.choice(string.ascii_letters + string.digits) for n in xrange(length)])
    
    
    
class CondorPool(models.Model):
    """Abstract placeholder for either an EC2 condor pool, or some other Bosco pool
    """
    
    name = models.CharField(max_length=100, verbose_name='Pool name', help_text='Choose a name for this pool')

    user = models.ForeignKey(User)
    
    uuid=UUIDField(auto=True, null=True, blank=True)
    
    copy_of = models.ForeignKey('self', blank=True, null=True, help_text = 'Is this pool a copy of an existing pool belonging to another user?')
    
    platform = models.CharField(max_length = 4,
                                verbose_name='The platform of the remote condor submitter we are connecting to',
                                choices = (
                                           ('DEB6', 'Debian 6'),
                                           ('RH5', 'Red Hat 5'),
                                           ('RH6', 'Red Hat 6'),
                                           ),
                                default='DEB6',
                                )
    
    address = models.CharField(max_length=200,
                               verbose_name = 'The full username@remote_address of the remote submitter',
                               blank=True,
                               default='',
                               )
    
    pool_type = models.CharField(max_length=20, choices = (
                                                           ('condor', 'Condor'),
                                                           ('pbs', 'PBS'),
                                                           ('lsf', 'LSF'),
                                                           ('sge', 'Sun Grid Engine'),
                                                           ),
                                 default='condor',
                                 )

    class Meta:
        #abstract = True
        app_label = 'web_interface'

    def get_pool_type(self, display=False):
        if hasattr(self, 'ec2pool'):
            if display:
                return 'EC2'
            else:
                return 'ec2'
        elif hasattr(self, 'boscopool'):
            if display:
                return self.get_pool_type_display()
            else:
                return 'bosco'
        else:
            return 'unknown'
        
    def __unicode__(self):
        if self.copy_of != None:
            return "%s (%s) (Shared)" % (self.name, self.get_pool_type(display=True))
        else:
            return "%s (%s)" % (self.name, self.get_pool_type(display=True))
    
    def get_pool_type_display_true(self):
        return self.get_pool_type(display=True)


    def get_running_tasks(self):
        return Task.objects.filter(condor_pool=self).filter(status='running')
    
class BoscoPool(CondorPool):
    """Store info about a non-EC2 pool added through Bosco
    """

    class Meta:
        app_label = 'web_interface'
    
class EC2Pool(CondorPool):
    """Stores info about all the EC2 instances  making up a condor pool#
    """
    vpc = models.ForeignKey(VPC, verbose_name='Keypair')
    master=models.ForeignKey('EC2Instance', null=True)
    size=models.PositiveIntegerField(verbose_name='Initial number of nodes', help_text='The number of compute nodes to launch. In addition, a master node will also be launched.')
    
    key_pair = models.ForeignKey('EC2KeyPair', null=True)

    initial_instance_type = models.CharField(max_length=20, choices=ec2_config.EC2_TYPE_CHOICES, blank=False, default='t1.micro', help_text='The instance type to launch. The price per hour will vary depending on the instance type. For more information on the different instance types see the <a href="">help page</a>.')

    secret_key = models.CharField(max_length=30, default=create_secret_key)
    
    
    
    last_update_time = models.DateTimeField(auto_now_add=True)
    

    #launch_configuration = models.CharField(max_length=20, help_text='The AWS launch configuration used for autoscaling')
    
    #autoscaling_group = models.CharField(max_length=20, help_text='The name of the AWS autoscaling group for this pool')
    
    #auto_scale_up = models.BooleanField(default=False, help_text='Not implemented at present')
    
    #auto_scale_down = models.BooleanField(default=True, help_text = 'Terminate unused worker nodes when they become inactive. Only applies after the first task has been submitted.')
    
    auto_terminate = models.BooleanField(default=True, help_text = 'Terminate all nodes of the pool after a task has been run if no other tasks are running. Only applies after at least one task has been submitted to the pool.')
    
    class Meta:
        app_label = 'web_interface'
        
    
    def get_key_pair(self, ec2_connection):
        return ec2_connection.get_key_pair(self.key_pair.name)
    
    def get_count(self):
        instances = EC2Instance.objects.filter(ec2_pool=self).filter(state='running')
        return instances.count()
    
    def get_queue_name(self):
        return "cloud-copasi-" + str(self.uuid) 
    
    def get_alarm_notify_topic(self):
        """Return the name of the SNS topic that has been created for this pool for instance alarm notifications
        """
        return 'cloud-copasi-' + str(self.uuid)
    
    alarm_notify_topic_arn = models.CharField(max_length = 80, blank=True, null=True)
    
    def get_health(self):
        instances = EC2Instance.objects.filter(ec2_pool=self)

        for instance in instances:
            if instance.get_health() != 'healthy' or instance.get_health != 'initializing': return instance.get_health()
        return 'healthy'
    
class EC2Instance(models.Model):
    
    ec2_pool = models.ForeignKey(EC2Pool)
    
    instance_type = models.CharField(max_length=20, choices=ec2_config.EC2_TYPE_CHOICES)
    
    instance_role = models.CharField(max_length=20,
                                     choices=(
                                              ('master', 'Master'),
                                              ('worker', 'Worker')
                                              )
                                     )
    
    instance_id = models.CharField(max_length=20,
                                   verbose_name='EC2 instance ID')
    #We ought to have a private IP associated. However, allow blank in case the
    #AWS API messes up. Can find out again later if need be
    
    state = models.CharField(max_length=20,
                             verbose_name = 'Last known state',
                             choices=(
                                      ('pending', 'Pending'),
                                      ('running', 'Running'),
                                      ('shutting-down', 'Shutting down'),
                                      ('terminated', 'Terminated'),
                                      ('stopping', 'Stopping'),
                                      ('stopped', 'Stopped'),
                                      ),
                             default='pending'
                             )
    
    #Any message associated with the state
    state_transition_reason = models.CharField(max_length=50, verbose_name = 'Why the instance changed state', blank=True, null=True)
    
    instance_status = models.CharField(max_length=20, default='initializing')
    system_status = models.CharField(max_length=20, default='initializing')
    
    termination_alarm = models.CharField(max_length=30, blank=True, null=True, verbose_name = 'The name of any attached low CPU usage termination alarm')
    
    def get_health(self):
        if self.instance_status=='ok' and self.system_status=='ok': return 'healthy'
        elif self.instance_status=='ok': return self.system_status
        else: return self.instance_status
    
    class Meta:
        app_label = 'web_interface'
        
    def __unicode__(self):
        return "EC2 instance %s" % self.instance_id
    
    def get_instance(self):
        ec2_connection = self.get_ec2_connection()
        instance_reservation = ec2_connection.get_all_instances(instance_ids=[self.instance_id])
        instance = instance_reservation[0].instances[0]
        
        return instance
    
    def get_ec2_connection(self):
        vpc_connection, ec2_connection = aws_tools.create_connections(self.ec2_pool.vpc.access_key)
        
        return ec2_connection

    def get_state(self):
        try:
            instance = self.get_instance()
            #instance.update()
            self.state = instance.state
            self.save()
            return instance.state
        except:
            return 'Error'
    def get_private_ip(self):
        instance=self.get_instance()
        return instance.private_ip_address

class SpotRequest(models.Model):
    ec2_pool = models.ForeignKey(EC2Pool)
    
    ec2_instance = models.ForeignKey(EC2Instance, null=True)
    
    request_id = models.CharField(max_length=20)
    
    max_price = models.FloatField()
    
    status_code = models.CharField(max_length=50)
    status_message = models.CharField(max_length = 500)
    
    state = models.CharField(max_length=20)
    
    
    class Meta:
        app_label = 'web_interface'
    
    def __unicode__(self):
        return "%s (User: %s)" % (self.name, self.vpc.access_key.user.username) 


class AMI(models.Model):
    """Stores information about an Amazon EC2 AMI
    """
    owner = models.IntegerField()
    
    name = models.CharField(max_length=100)
    
    version = models.CharField(max_length=100, blank=True)
    
    image_id=models.CharField(max_length=20)
    
    active = models.BooleanField()
    
    class Meta:
        app_label = 'web_interface'
        
    def __unicode__(self):
        return self.name
    
class EC2KeyPair(models.Model):
    name = models.CharField(max_length=20, verbose_name='EC2 Key Pair name')
    
    path = models.CharField(verbose_name = 'Location of the public key pair', max_length=255)
    
    class Meta:
        app_label = 'web_interface'
        
    def __unicode__(self):
        return self.name
    
class ElasticIP(models.Model):
    public_ip = models.IPAddressField()
    
    instance=models.OneToOneField(EC2Instance, null=True)
    
    vpc = models.ForeignKey(VPC)
    
    allocation_id = models.CharField(max_length=20, verbose_name='The allocation ID for the IP address')
    
    association_id = models.CharField(max_length=20, verbose_name='The instance association ID for the address')
    
    class Meta:
        app_label = 'web_interface'
        
    def __str__(self):
        return self.public_ip
    

class Task(models.Model):
    """High-level representation of a computing job
    """

    condor_pool = models.ForeignKey(CondorPool)
     
    name = models.CharField(max_length=100, verbose_name='The name of the computing job')
    
    submit_time = models.DateTimeField(auto_now_add=True)
    finish_time = models.DateTimeField(null=True, blank=True)
    last_update_time = models.DateTimeField(auto_now=True)
    task_type = models.CharField(max_length=128, )
    
    #Filename of the original model (relative path only)
    original_model = models.CharField(max_length=200)
    #And the full path of the directory the task files are stored in
    directory = models.CharField(blank=True, default='not_set', max_length=255)
    
    #Field for storing any task-specific fields
    #Will be stored as a string-based python pickle
    #Not the most efficient way of doing this, but these fields unlikely to be needed much
    
    result_view = models.BooleanField(blank=True, default=True, verbose_name='Does this task type have a result view page?')
    result_download = models.BooleanField(blank=True, default=True, verbose_name='Does this task type have a result download page?')
    
    custom_fields = models.CharField(max_length=10000, blank=True, default='')

    def set_custom_field(self, field_name, value):
        try:
            custom_fields = json.loads(self.custom_fields)
        except:
            custom_fields = {}
        custom_fields[field_name] = value
        self.custom_fields = str(json.dumps(custom_fields))
        self.save()
    
    def get_custom_field(self, field_name):
        try:
            custom_fields_str = str(self.custom_fields)
            custom_fields = json.loads(custom_fields_str)
            output = custom_fields[field_name]
            return output
        except Exception, e:
            return None
    
    status_choices = (
                      ('new', 'New'),
                      ('running', 'Running'),
                      ('finished', 'Finished'),
                      ('error', 'Error'),
                      ('delete', 'Deleted'),
                      ('cancelled', 'Cancelled'),
                      ('unknown', 'Unknown'),
                      )
    
    
    status = models.CharField(verbose_name = 'The status of the task', max_length=32, choices = status_choices, default='waiting')
    
    
    def update_cpu_time(self):
        """Go through each of the subtasks, and in turn the CondorJobs, and collate the run times
        """
        #TODO:
        pass
    
    def update_status(self):
        """Go through the attached subtasks and update the status based on their status
        """
        subtasks = Subtask.objects.filter(task=self)
        if subtasks.count() == 0:
            self.status = 'new'
        else:
            all_finished = True
            error = False
            delete = False
            for subtask in subtasks:
                if subtask.status != 'finished' : all_finished = False
                elif subtask.status == 'error': error = True
                elif subtask.status == 'delete': delete = True
            
            if all_finished:
                #If all subtasks are marked as finished, then mark the task status as also finished
                self.status = 'finished' 
            if error:
                #A single error - mark the task as error too
                self.status = 'error'
            if delete:
                self.status = 'delete'
        
        self.save()
        
    def get_outgoing_bucket_name(self):
        return None

    def get_incoming_bucket_name(self):
        return None

        
    def get_outgoing_bucket(self):
        
        s3_connection = s3_tools.create_s3_connection(self.condor_pool.vpc.access_key)
        bucket=s3_connection.get_bucket(self.get_outgoing_bucket_name())
        return bucket
    
    def get_incoming_bucket(self):
        s3_connection = s3_tools.create_s3_connection(self.condor_pool.vpc.access_key)
        bucket=s3_connection.get_bucket(self.get_incoming_bucket_name())
        return bucket

    def get_job_count(self):
        """Return the number of jobs associated.
        If the number of CondorJobs is 0, return self.job_count instead
        """
        
        if self.job_count > 0:
            return self.job_count
        else:
            count = 0
            subtasks = Subtask.objects.filter(task=self) 
            for subtask in subtasks:
                count += subtask.get_job_count()
            return count
    def set_job_count(self):
        self.job_count = self.get_job_count()
        self.save()
        
    job_count = models.IntegerField(default=-1, help_text = 'The count of the number of condor jobs. Only set after the subtask has finished. Use get_job_count() instead to find out job count')
    
    def get_run_time(self):
        """Return the run time of the subtask. If the value hasn't been set, the look through the associated condor jobs and get from there
        """
        
        if self.run_time > 0:
            return self.run_time
        else:
            subtasks = self.subtask_set.all()
            count = 0
            for subtask in subtasks:
                count += subtask.get_run_time()
            return count
    def set_run_time(self):
        self.run_time = self.get_run_time()
        self.save()
    
    def get_run_time_timedelta(self): return datetime.timedelta(days=self.get_run_time())    
    run_time = models.FloatField(default=-1.0, help_text = 'The run time of associated condor jobs. Only set after the subtask has finished. Use get_run_time() to access.')

    
    class Meta:
        app_label = 'web_interface'
        
    def __unicode__(self):
        return self.name
    
    
    def trim_condor_jobs(self):
        """Delete all the associated condor jobs.
        Typically used when a task has finished or is being marked as deleted
        Updates job_count and run_time before deleting
        """
        
        self.set_run_time()
        self.set_job_count()
        
        subtasks = self.subtask_set.all()
        for subtask in subtasks:
            jobs = subtask.condorjob_set.all()
            for job in jobs:
                job.delete()
    
    
class Subtask(models.Model):
    
    task = models.ForeignKey(Task, null=True)
    
    index = models.PositiveIntegerField(verbose_name = 'The order in this subtask is to be executed')
    
    active = models.BooleanField(default=False)
    
    type_choices = (
                    ('lb', 'Load balancing'),
                    ('main', 'Main task'),
                    ('process', 'Results processing'),
                    ('file', 'Creating file with optimal values'),
                    ('other', 'Other'),
                    )
    
    type = models.CharField(max_length=32, choices=type_choices)
    
    status_choices = (
                      ('waiting', 'Waiting'),
                      ('ready', 'Ready'),
                      ('running', 'Running'),
                      ('finished', 'Finished'),
                      ('error', 'Error'),
                      ('delete', 'Marked for deletion'), #TODO: needed?
                      ('unkown', 'Unknown'),
                      )
    status = models.CharField(max_length=32, choices = status_choices, default='waiting')
    
    cluster_id = models.IntegerField(blank=True, null=True) #The condor cluster ID (i.e. $(Cluster)) 
    
    spec_file = models.spec_file = models.CharField(max_length=255, blank=True)
    
    local = models.BooleanField(blank=True, default=False, help_text = 'Is this subtask to be run locally?')

    custom_fields = models.CharField(max_length=10000, blank=True, default='')

    def set_custom_field(self, field_name, value):
        try:
            custom_fields = json.loads(self.custom_fields)
        except:
            custom_fields = {}
        custom_fields[field_name] = value
        self.custom_fields = str(json.dumps(custom_fields))
        self.save()
    
    def get_custom_field(self, field_name):
        try:
            custom_fields_str = str(self.custom_fields)
            custom_fields = json.loads(custom_fields_str)
            output = custom_fields[field_name]
            return output
        except Exception, e:
            return None

    def get_job_count(self):
        """Return the number of jobs associated.
        If the number of CondorJobs is 0, return self.job_count instead
        """
        if self.job_count > 0:
            return self.job_count
        else:
            jobs = self.condorjob_set.all()
            return max(jobs.count(), 0)
   
    def set_job_count(self):
        self.job_count = self.get_job_count()
        self.save() 
    job_count = models.IntegerField(default=-1, help_text = 'The count of the number of condor jobs. Only set after the subtask has finished. Use get_job_count() instead to find out job count')
    
    
    def get_run_time(self):
        """Return the run time of the subtask. If the value hasn't been set, the look through the associated condor jobs and get from there
        """
        
        if self.run_time > 0:
            return self.run_time
        else:
            jobs = self.condorjob_set.all()
            count = 0
            for job in jobs:
                count += job.run_time
            return count
    def set_run_time(self, time_delta=None):
        if not time_delta:
            self.run_time = self.get_run_time()
        else:
            assert isinstance(time_delta, datetime.timedelta)
            #Calculate run time in days
            self.run_time = time_delta.days +  (float(time_delta.seconds) / 86400.00)
        self.save()
    def get_run_time_timedelta(self): return datetime.timedelta(days=self.get_run_time())
    
    run_time = models.FloatField(default=-1.0, help_text = 'The cumulative run time of associated condor jobs in days. Only set after the subtask has finished. Use get_run_time() to access.')
    
    start_time=models.DateTimeField(blank=True, null=True, help_text= 'The time this subtask started running')
    finish_time = models.DateTimeField(blank=True, null=True, help_text = 'The time the subtask stopped running')
    
    
    def __unicode__(self):
        return '%s (%d)' % (self.task.name, self.index)
    
class CondorJob(models.Model):
    
    #The parent job
    subtask = models.ForeignKey(Subtask, null=True)
    #The std output file for the job
    std_output_file = models.CharField(max_length=255)
    #The log file for the job
    log_file = models.CharField(max_length=255)
    #The error file for the job
    std_error_file = models.CharField(max_length=255)
    #The output file created by the job
    job_output = models.CharField(max_length=255, blank=True)
    #The status of the job in the queue
    QUEUE_CHOICES = (
        ('N', 'Not queued'),
        ('I', 'Idle'),
        ('R', 'Running'),
        ('H', 'Held'),
        ('F', 'Finished'),
        ('D', 'Mark for deletion'),
        ('U', 'Unknown'),
        ('E', 'Error'),
    )
    status = models.CharField(max_length=1, choices=QUEUE_CHOICES)
    
    #The id of the job process in the cluster. Only set once the job has been queued. 
    process_id = models.IntegerField(null=True, blank=True)
    #The amount of computation time in days that the condor job took to finish. Note, this does not include any interrupted runs. Will not be set until the condor job finishes.
    run_time = models.FloatField(null=True)
    
    runs = models.PositiveIntegerField(verbose_name='The number of runs this particular job is performing', blank=True, null=True)
    
    #The copasi file that is to be copied over with this condor job
    copasi_file = models.CharField(max_length=255)
    
    def __unicode__(self):
        return '%s (%d - %d)' % (self.subtask.task.name, self.subtask.index, self.process_id)
        
        
    def getDirectory(self):
        return os.path.dirname(self.spec_file)
    
    class Meta:
        app_label = 'web_interface'