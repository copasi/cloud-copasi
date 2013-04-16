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
from fields import UUIDField

class AWSAccessKey(models.Model):
    """Represents an AWS access key
    """
    user = models.ForeignKey(User)
    
    name = models.CharField(max_length=100, help_text='For your convenience, assign a unique name to this access key', verbose_name='Key name')

    access_key_id = models.CharField(max_length=20, help_text='The 20-character AWS access key ID', verbose_name='Access key ID', validators=[RegexValidator(regex='^.{20}$', message='Length has to be 20', code='nomatch')])
    
    secret_key = models.CharField(max_length=40, help_text='The 40-character secret access key associated with the access key ID', verbose_name='Secret access key', validators=[RegexValidator(regex='^.{40}$', message='Length has to be 40', code='nomatch')])
    
    def __unicode__(self):
        return "%s, %s" % (self.name, self.access_key_id)
    
    class Meta:
        app_label = 'web_interface'
        unique_together = (('user', 'name'), ('user', 'access_key_id'))

class VPC(models.Model):
    """Represents an AWS VPC in which we can run jobs
    """
    access_key = models.OneToOneField(AWSAccessKey)
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
    """Stores info about all the EC2 instances  making up a condor pool#
    """
    vpc = models.ForeignKey(VPC, verbose_name='Keypair')
    master=models.OneToOneField('EC2Instance', null=True)
    name = models.CharField(max_length=100, verbose_name='Pool name', help_text='Choose a name for this pool')
    size=models.PositiveIntegerField(verbose_name='Number of nodes', help_text='The number of compute nodes to launch. In addition, a master node will also be launched.')
    
    key_pair = models.OneToOneField('EC2KeyPair', null=True)

    initial_instance_type = models.CharField(max_length=20, choices=ec2_config.EC2_TYPE_CHOICES, blank=False, default='t1.micro', help_text='The instance type to launch. The price per hour will vary depending on the instance type. For more information on the different instance types see the <a href="">help page</a>.')

    secret_key = models.CharField(max_length=30, default=create_secret_key)
    
    uuid=UUIDField(auto=True)
    
    class Meta:
        app_label = 'web_interface'
    
    def __unicode__(self):
        return "%s (User: %s)" % (self.name, self.vpc.access_key.user.username) 
    
    def get_status(self):
        return 'Not implemented'
    
    def get_key_pair(self, ec2_connection):
        return ec2_connection.get_key_pair(self.key_pair.name)
    
    def get_count(self):
        instances = EC2Instance.objects.filter(condor_pool=self)
        return instances.count()
    
    def get_queue_name(self):
        return "cloud-copasi-" + str(self.uuid) 
    
class EC2Instance(models.Model):
    
    condor_pool = models.ForeignKey(CondorPool)
    
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
        vpc_connection, ec2_connection = aws_tools.create_connections(self.condor_pool.vpc.access_key)
        
        return ec2_connection

    def get_state(self):
        instance = self.get_instance()
        #instance.update()
        return instance.state
    
    def get_private_ip(self):
        instance=self.get_instance()
        return instance.private_ip_address

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
    
    path = models.FilePathField(verbose_name = 'Location of the public key pair')
    
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
    uuid=UUIDField(auto=True)

    condor_pool = models.ForeignKey(CondorPool)
     
    name = models.CharField(max_length=100, verbose_name='The name of the computing job')
    

    
    task_type = models.CharField(max_length=128, )
    
    min_runs = models.PositiveIntegerField(verbose_name = 'The minimum number of repeats to perform', blank=True, null=True)
    max_runs = models.PositiveIntegerField(verbose_name = 'The maximum number of repeats to perform', blank=True, null=True)
    
    original_model = models.CharField(max_length=200)
    
    
    
    status_choices = (
                      ('N', 'New'),
                      ('R', 'Running'),
                      ('F', 'Finished'),
                      ('E', 'Error'),
                      ('D', 'Marked for deletion'),
                      ('U', 'Unknown'),
                      )
    
    
    status = models.CharField(verbose_name = 'The status of the task', max_length=32, choices = status_choices)
    
    
    
    def get_outgoing_bucket_name(self):
        return "cloud-copasi-out-%s" % self.uuid

    def get_incoming_bucket_name(self):
        return "cloud-copasi-in-%s" % self.uuid

        
    def get_outgoing_bucket(self):
        
        s3_connection = s3_tools.create_s3_connection(self.condor_pool.vpc.access_key)
        bucket=s3_connection.get_bucket(self.get_outgoing_bucket_name())
        return bucket
    
    def get_incoming_bucket(self):
        s3_connection = s3_tools.create_s3_connection(self.condor_pool.vpc.access_key)
        bucket=s3_connection.get_bucket(self.get_incoming_bucket_name())
        return bucket


    
    class Meta:
        app_label = 'web_interface'
        
    def __unicode__(self):
        return self.name
    
    
class Subtask(models.Model):
    
    task = models.ForeignKey(Task, null=True)
    
    index = models.PositiveIntegerField(verbose_name = 'The order in this subtask is to be executed')
    
    type_choices = (
                    ('benchmark', 'Benchmark'),
                    ('main', 'Main task'),
                    ('process', 'Results processing'),
                    ('other', 'Other'),
                    )
    
    type = models.CharField(max_length=32, choices=type_choices)
    
    status_choices = (
                      ('new', 'New'),
                      ('ready', 'Ready to queue'),
                      ('queued', 'Queued'),
                      ('finished', 'Finished'),
                      ('error', 'Error'),
                      ('delete', 'Marked for deletion'), #TODO: needed?
                      ('unkown', 'Unknown'),
                      )
    status = models.CharField(max_length=32, choices = status_choices)

    
class CondorJob(models.Model):
    
   #The parent job
    subtask = models.ForeignKey(Subtask, null=True)
    #The .job condor specification file
    spec_file = models.FilePathField(max_length=255)
    #The std output file for the job
    std_output_file = models.FilePathField(max_length=255)
    #The log file for the job
    log_file = models.FilePathField(max_length=255)
    #The error file for the job
    std_error_file = models.FilePathField(max_length=255)
    #The output file created by the job
    job_output = models.FilePathField(max_length=255)
    #The status of the job in the queue
    QUEUE_CHOICES = (
        ('C', 'Not copied'),
        ('N', 'Not queued'),
        ('Q', 'Queued'),
        ('I', 'Idle'),
        ('R', 'Running'),
        ('H', 'Held'),
        ('F', 'Finished'),
        ('D', 'Mark for deletion'),
        ('U', 'Unknown'),
        ('E', 'Error'),
    )
    queue_status = models.CharField(max_length=1, choices=QUEUE_CHOICES)
    #The id of the job in the queue. Only set once the job has been queued
    queue_id = models.IntegerField(null=True)
    #The amount of computation time in seconds that the condor job took to finish. Note, this does not include any interrupted runs. Will not be set until the condor job finishes.
    run_time = models.FloatField(null=True)
    
    runs = models.PositiveIntegerField(verbose_name='The number of runs this particular job is performing', blank=True, null=True)
    
    #The copasi file that is to be copied over with this condor job
    copasi_file = models.FilePathField(max_length=255)
    
    def __unicode__(self):
        return "%s (task %s)" % (unicode(self.queue_id), self.task.name)
        
        
    def getDirectory(self):
        return os.path.dirname(self.spec_file)
    
    class Meta:
        app_label = 'web_interface'