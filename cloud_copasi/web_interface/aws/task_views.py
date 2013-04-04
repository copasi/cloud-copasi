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
from cloud_copasi.web_interface.models import AWSAccessKey, VPC, CondorPool, CondorJob, Task
from cloud_copasi.web_interface import models
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import sys
from cloud_copasi.web_interface.account.account_views import MyAccountView
from django.contrib.auth.forms import PasswordChangeForm
from boto.vpc import VPCConnection
from boto.ec2 import EC2Connection
from cloud_copasi.web_interface.aws import vpc_tools, task_tools
import tempfile, os
from cloud_copasi import settings
from cloud_copasi.copasi.model import CopasiModel

class NewTaskForm(forms.Form):
    name = forms.CharField()
    task_type = forms.Select(choices=models.TASK_CHOICES)
    number_of_nodes = forms.IntegerField()
    aws_access_key = forms.ChoiceField()
    model_file = forms.FileField
    compute_pool = forms.ChoiceField()
    
    def __init__(self, user, *args, **kwargs):
        super(NewTaskForm, self).__init__(*args, **kwargs)
        self.user = user
        vpcs = VPC.objects.filter(access_key__user=self.user)
        self.fields['aws_access_key'].choices = ( (x.access_key, x.access_key.name) for x in vpcs)
        condor_pools = CondorPool.objects.filter(vpc__access_key__user = user)
        self.fields['compute_pool'].choices = ((x, x.name) for x in condor_pools)
#Generic function for saving a django UploadedFile to a destination
def handle_uploaded_file(f,destination):
    #destination = open(destination, 'wb+')
    for chunk in f.chunks():
        destination.write(chunk)
    #destination.close()

class NewTaskView(RestrictedFormView):
    template_name = 'tasks/task_new.html'
    page_title = 'New task'
    form_class = NewTaskForm
    
    def get_form_kwargs(self):
        kwargs = super(NewTaskView, self).get_form_kwargs()
        kwargs['user']=self.request.user
        return kwargs
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        #Ensure we have at least 1 running condor pool
        pools = CondorPool.objects.filter(vpc__access_key__user=request.user)
        if pools.count() == 0:
            request.session['errors']=[('No running compute pools', 'You must have at least 1 running compute pool before you can submit a job')]
            return HttpResponseRedirect(reverse_lazy('pool_status'))
        return super(NewTaskView,self).dispatch(request, *args, **kwargs)
    
    def form_valid(self, form,  *args, **kwargs):
        access_key = form.cleaned_data['aws_access_key']
        compute_pool = form.cleaned_data['compute_pool']
        request = self.request

        assert access_key.user == request.user
        assert compute_pool.vpc.access_key == access_key
        
        ########################################################################
        #Process the uploaded copasi file (and other files?) and create a list
        #of files to upload to s3
        ########################################################################
        
        #Handle uploaded files...
        #Ensure the directory we're adding the file to exists
        os.mkdir(settings.STORAGE_DIR)
        
        working_file = tempfile.TemporaryFile(mode='w', dir=settings.STORAGE_DIR)
        handle_uploaded_file(request.files['model_file'], working_file)
        working_file.close()
        
        
        ##TODO:Do this for any data files too
        #Check the file is valid for the task type
        ##TODO: implement
        
        ########################################################################
        #Process the model file and create the neccesary files needed for
        #submitting the condor jobs
        ########################################################################
        
        copasi_model = CopasiModel(working_file.name, task_type = form.cleaned_data['task_type'])
        
        condor_jobs, model_files = copasi_model.create_condor_jobs()
        
        ########################################################################
        #Next, create the new task object and send the files over to s3
        ########################################################################
        #try:
        task = Task()
        task.name = form.cleaned_data['name']
        task.condor_pool = CondorPool.objects.get(id=form.cleaned_data['pool'])
        task.task_type = form.cleaned_data['task_type']
        task.runs = form.cleaned_data['min_runs']
        task.max_runs = form.cleaned_data['max_runs']
        
        filepath, filename = os.path.split(request.files['model_file'].name)
        
        task.original_model = filename
        
        task.save()
        
        
        
        #List of full file paths
        file_list = model_files + data_files
        
        key_names = job_tools.store_to_outgoing_bucket(task, file_list)
        
        
        ########################################################################
        #Notify the pool queue that a new task has been submitted
        ########################################################################
        
        #get a list of the file names of the 
        
        job_tools.notify_new_task(task, key_names)
        
        #except:
        #unto anything performed here and delete files
        
        return HttpResponseRedirect(reverse_lazy('my_account_job_new'))
    
class JobNewView(RestrictedView):
    pass
