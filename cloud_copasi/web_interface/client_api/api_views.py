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
from cloud_copasi.web_interface.aws import vpc_tools, aws_tools
from cloud_copasi.web_interface import models, task_plugins
from django.views.decorators.cache import never_cache
from boto.exception import EC2ResponseError, BotoServerError
import boto.exception
from cloud_copasi.web_interface.models import VPC, CondorPool, Task, CondorJob, Subtask
from django.http import HttpRequest
import json
from django.views.decorators.csrf import csrf_exempt

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
                TaskClass = task_plugins.get_class(subtask.task.task_type)
                
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
    Respond to notificationt that files have been transferred
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