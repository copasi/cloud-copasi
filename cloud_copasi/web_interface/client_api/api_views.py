#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
from django.views.generic import TemplateView, RedirectView, View, FormView
from django.views.generic.edit import FormMixin, ProcessFormView
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django import forms
from cloud_copasi.web_interface.views import RestrictedView, DefaultView, RestrictedFormView
from cloud_copasi.web_interface.models import AWSAccessKey, CondorJob, Subtask
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import sys
from django.contrib.auth.forms import PasswordChangeForm
from cloud_copasi.web_interface.aws import vpc_tools, aws_tools,\
    resource_management_tools, ec2_tools
from cloud_copasi.web_interface import models, task_plugins
from django.views.decorators.cache import never_cache
from boto.exception import EC2ResponseError, BotoServerError
import boto.exception
from cloud_copasi.web_interface.models import VPC, CondorPool, Task, CondorJob, Subtask
from django.http import HttpRequest
import json, logging
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from cloud_copasi.web_interface.task_plugins import base, tools
import urllib2

log = logging.getLogger(__name__)
class APIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(APIView, self).dispatch(request, *args, **kwargs)


class UpdateJobStatusView(APIView):
    """
    Update the status of a particular job without changing the status of individual condor jobs
    """
    
    def post(self, request, *args, **kwargs):
        pass

class RegisterJobView(APIView):
    """
    Register the queue ids of condor jobs
    """ 

    def post(self, request, *args, **kwargs):
        assert isinstance(request, HttpRequest)
        assert request.META['CONTENT_TYPE'] == 'application/json'
        
        json_data=request.body
        data = json.loads(json_data)
        
        pool_id = data['pool_id']
        secret_key = data['secret_key']
        
        pool=CondorPool.objects.get(uuid=pool_id)
        #Validate that we trust this pool
        assert pool.secret_key == secret_key
        #Update the Condor jobs with their new condor q id
        for condor_job_id, queue_id in data['condor_jobs']:
            condor_job = CondorJob.objects.get(id=condor_job_id)
            assert condor_job.subtask.task.condor_pool == pool
            condor_job.queue_id = queue_id
            condor_job.queue_status = 'I'
            condor_job.save()
        
        try:
            #Set the subtask status as active. Look at the last condor_jobn
            subtask = condor_job.subtask
            subtask.status = 'queued'
            subtask.save()
        except:
            #Test case - no condor jobs submitted, therefore we can't know which subtask was updated
            pass
        
        
        #Now a task has been submitted, add termination alarms to the instances if this has been requested.

        try:
            ec2_tools.add_instances_alarms(pool)
        except Exception, e:
            log.exception(e)
                

        
        
        #Construct a json response to send back
        response_data={'status':'created'}
        json_response=json.dumps(response_data)
        
        return HttpResponse(json_response, content_type="application/json", status=201)
    
class UpdateCondorStatusView(APIView):
    """
    Update the queue ids of condor jobs
    """ 
    

    def post(self, request, *args, **kwargs):
        assert isinstance(request, HttpRequest)
        assert request.META['CONTENT_TYPE'] == 'application/json'
        json_data=request.body
        data = json.loads(json_data)

        pool_id = data['pool_id']
        secret_key = data['secret_key']
        
        
        pool=CondorPool.objects.get(uuid=pool_id)
        assert pool.secret_key == secret_key
        
        
        #Get the condor jobs associated with the condor pool which we think are still running
        pool_jobs = CondorJob.objects.filter(subtask__task__condor_pool=pool)
        running_jobs = pool_jobs.filter(queue_status='R')
        idle_jobs = pool_jobs.filter(queue_status='I')
        held_jobs = pool_jobs.filter(queue_status='H')
        
        queued_jobs = running_jobs | idle_jobs | held_jobs
        
        
        for condor_queue_id, queue_status in data['condor_jobs']:
            condor_job = queued_jobs.get(queue_id=condor_queue_id)
            condor_job.queue_status=queue_status
            condor_job.save()
            
            #Since this job appeared in the list, it's not finished
            
            queued_jobs = queued_jobs.exclude(id=condor_job.id)
        
        #Assume that everything left in queued_jobs has finished
        for job in queued_jobs:
            job.queue_status = 'F'
            job.save()

        
        #Get all subtasks that are running on the pool
        
        active_subtasks = Subtask.objects.filter(task__condor_pool=pool).filter(active=True)
        
        for subtask in active_subtasks:
            #Look at all the jobs. Are they all finished?
            all_jobs_finished = True
            errors = False
            
            for job in subtask.condorjob_set.all():
                if job.queue_status != 'F':
                    all_jobs_finished = False
                elif job.queue_status == 'H':
                    errors = True
            
            if errors:
                print sys.stderr, 'Error!'
                subtask.active=False
                subtask.status='error'
                subtask.save()
                subtask.task.status='error'
                subtask.task.save()
                
            elif all_jobs_finished:
                print >>sys.stderr, 'All jobs finished'
                subtask.active = False
                subtask.status = 'finished'
                subtask.save()
                
                
                #Is there another subtask to run?
                TaskClass = tools.get_task_class(subtask.task.task_type)
                
                subtask_count = TaskClass.subtasks
                
                task_instance = TaskClass(subtask.task)
                
                if subtask.index < subtask_count:
                    #We have another subtask to run
                    print 'Another subtask to run!'
                    
                    task_instance.submit_subtask(subtask.index + 1)
                    
                else:
                    #The task must have finished
                    #Request the transfer of files
                    task_instance.request_file_transfer(subtask.index, 'finished')
                    
        
        #Finally, add instance alarms to the task if needed:
        try:
            ec2_tools.add_instances_alarms(pool)
        except Exception, e:
            log.exception(e)

        
        #Construct a json response to send back
        response_data={'status':'created'}
        json_response=json.dumps(response_data)
        
        return HttpResponse(json_response, content_type="application/json", status=201)

class RegisterDeletedJobsView(APIView):
    """
    Respond to notificationt that jobs have been deleted
    """ 
    

    def post(self, request, *args, **kwargs):
        assert isinstance(request, HttpRequest)
        assert request.META['CONTENT_TYPE'] == 'application/json'
        json_data=request.body
        data = json.loads(json_data)

        pool_id = data['pool_id']
        secret_key = data['secret_key']
        
        pool=CondorPool.objects.get(uuid=pool_id)
        assert pool.secret_key == secret_key
        
        
        
        for job_id in data['job_list']:
            try:
                job = CondorJob.objects.get(queue_id=job_id)
                assert job.subtask.task.condor_pool == pool
                
                subtask = job.subtask
                
                job.delete()
                
                if subtask.condorjob_set.count() == 0:
                    subtask.delete()
            except:
                print >>sys.stderr, "Couldn't delete job %d" % job_id
        #Construct a json response to send back
        response_data={'status':'created'}
        json_response=json.dumps(response_data)
        
        return HttpResponse(json_response, content_type="application/json", status=201)

class RegisterTransferredFilesView(APIView):
    """
    Respond to notifications that files have been transferred
    """ 
    

    def post(self, request, *args, **kwargs):
        assert isinstance(request, HttpRequest)
        assert request.META['CONTENT_TYPE'] == 'application/json'
        json_data=request.body
        data = json.loads(json_data)

        pool_id = data['pool_id']
        secret_key = data['secret_key']
        
        pool=CondorPool.objects.get(uuid=pool_id)
        assert pool.secret_key == secret_key
        
        task = Task.objects.get(uuid=data['task_uuid'])
        
        for file_key in data['file_list']:
            pass
        
        #After transferring files, look at why the transfer took place
        
        reason = data['reason']
        
        if reason=='error':
            task.status = 'error'
        elif reason=='finished':
            task.status = 'finished'
        elif reason=='cancelled':
            task.status='cancelled'
            
        task.save()
        #Construct a json response to send back
        response_data={'status':'created'}
        json_response=json.dumps(response_data)
        
        return HttpResponse(json_response, content_type="application/json", status=201)
    
class RemoteLoggingUpdateView(APIView):
    """Receive a log from a remote server, store it, and acknowledge the message was received
    """
    def post(self, request, *args, **kwargs):
        assert isinstance(request, HttpRequest)
        assert request.META['CONTENT_TYPE'] == 'application/json'
        json_data=request.body
        data = json.loads(json_data)

        pool_id = data['pool_id']
        secret_key = data['secret_key']
        
        pool=CondorPool.objects.get(uuid=pool_id)
        assert pool.secret_key == secret_key
        
        #Message list contains tuples (message type, datetime, message)
        message_list = data['message_list']
        
        for message_type, date_time, message in message_list:
            
            if message_type == 'debug':
                log_method = log.debug
            elif message_type == 'info':
                log_method = log.info
            elif message_type == 'warning':
                log_method = log.warning
            elif message_type == 'error':
                log_method = log.error
            elif message_type == 'critical':
                log_method = log.critical
            else:
                continue
            pool_name = pool.name
            pool_username = pool.vpc.access_key.user.username
            
            log_message = '[%s] Message from pool %s (user %s): %s' % (date_time, pool_name, pool_username, message)
            
            log_method(log_message)
        
        #Construct a json response to send back
        response_data={'status':'created'}
        json_response=json.dumps(response_data)
        
        return HttpResponse(json_response, content_type="application/json", status=201)

    
class CheckResourceView(APIView):
    
    def get(self, request, *args, **kwargs):
        user_id = int(request.GET['user_id'])
        user = User.objects.get(id=user_id)
        log.debug('Checking status for user %s'%user)

        try:
            if not resource_management_tools.get_unrecognized_resources(user).is_empty():
                status='unrecognized'
            elif resource_management_tools.get_local_resources(user).is_empty():
                status='empty'
            else:
                health = resource_management_tools.health_check(user)
                log.debug('health : %s'%health)
                if health == 'initializing': status = 'pending'
                elif health == 'healthy': status ='healthy'
                else: status = 'problem'
            
        except Exception, e:
            log.exception(e)
            status='error'
            
        response_data = {'status' : status}
        json_response=json.dumps(response_data)
        return HttpResponse(json_response, content_type="application/json", status=200)
    
class ExtraTaskFieldsView(APIView):
    """Return the extra fields required for a specific task. Typically called asynchronously
    """
    def get(self, request, *args, **kwargs):
        task_type = request.GET['task_type']
        
        task_form = tools.get_form_class(task_type)
        
        base_form = base.BaseTaskForm
        
        #Get a list of all fields that are only in the task form, and not in the base
        extra_fields = []
        for field_name in task_form.base_fields:
            if field_name not in base_form.base_fields:
                extra_fields.append(field_name)
        
        #Create a bound instance of the task form so we can get at the html
        bound_form = task_form(user=None, task_types=[])
        field_list = []
        
        #Return the complete html here:
        
        
        for field_name in extra_fields:
            field = bound_form[field_name]
            field_data=  {}
            #print field
            field_data['label'] = field.label
            field_data['field'] = str(field) #should be html
            if field.field.required:
                field_data['required'] = 'required'
            else:
                field_data['required'] = ' '
            if field.help_text:
                field_data['help_text'] = field.help_text
            else:
                field_data['help_text'] = ' '
            field_data['id'] = field.id_for_label
            field_data['html_name'] = field.html_name
            
            field_list.append(field_data)
        response_data={}
        response_data['fields'] = field_list
        json_response=json.dumps(response_data)
        return HttpResponse(json_response, content_type="application/json", status=200)
    
class TerminateInstanceAlarm(APIView):
    """Receive a notification from an alarm to terminate an instance due to inactivity.
    If this happens, we have to also cancel any associated spot requests or the instance will respawn!
    """

    def post(self,request, *args, **kwargs ):
        assert isinstance(request, HttpRequest)
        json_data=request.body
        data = json.loads(json_data)
        
        #If this is a subscription confirmation message, then confirm the request
        if data['Type'] == 'SubscriptionConfirmation':
            connection = urllib2.urlopen(data['SubscribeURL'])
            log.debug('Request to subscribe to termination alarm subscription')
            assert connection.getcode() == 200
            log.debug('Successfully subscribed')
            connection.close()
        
        elif data['Type'] == 'Notification':
            log.debug('Received assumed alarm termination notification')
            log.debug(data['Subject'])
            
            #load the message as another json object
            message_data = json.loads(data['Message'])
            
            alarm_name = message_data['AlarmName']
            
            #Get the instance with this alarm
            try:
                instance = models.EC2Instance.objects.get(termination_alarm=alarm_name)
                log.debug('Terminating instance %s due to inactivity'%instance.instance_id)
                ec2_tools.terminate_instances([instance])
            except Exception, e:
                log.exception(e)
                return HttpResponse(status=500)

        return HttpResponse(status=200)
