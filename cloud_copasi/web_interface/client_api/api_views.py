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
from cloud_copasi.web_interface import models
from django.views.decorators.cache import never_cache
from boto.exception import EC2ResponseError, BotoServerError
import boto.exception
from cloud_copasi.web_interface.models import VPC, CondorPool, Task, CondorJob
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
            condor_job.queue_id = queue_id
            condor_job.save()
        
        
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
        
        
        #Get the tasks associated with the condor pool which are still running
        #Create a store for each task with count 0
        #e.g. count={}, count['odigljdklfgjdhpshpj'] = 0...
        count = {}
        subtasks = Subtask.objects.filter(task__condor_pool=pool).filter(status='queued')
        for subtask in subtasks:
            count[subtask.id] = 0
        
        
        
        #Go through the condor jobs in the response
        ##Update job statuses as required
        #Increase the count for the task by 1
        
        #Any job with count 0 has finished running.
        
        for condor_queue_id, queue_status in data['condor_jobs']:
            #TODO: put in try, except blocks
            condor_job = CondorJob.objects.get(queue_id=condor_queue_id)
            condor_job.queue_status = queue_status
            condor_job.save()
            
            subtask = condor_job.subtask
            count[subtask.id] += 1
        
        for subtask in subtasks:
            if count[subtask.id] == 0:
                subtask.status = 'finished'
                subtask.save()
                #TODO:Is there another subtask to submit?
        
        
        #Construct a json response to send back
        response_data={'status':'created'}
        json_response=json.dumps(response_data)
        
        return HttpResponse(json_response, content_type="application/json", status=201)
