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
from cloud_copasi.web_interface.models import AWSAccessKey, VPC, CondorPool, CondorJob, Task, Subtask
from cloud_copasi.web_interface import models, aws
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import sys
from cloud_copasi.web_interface.account.account_views import MyAccountView
from django.contrib.auth.forms import PasswordChangeForm
from boto.vpc import VPCConnection
from boto.ec2 import EC2Connection
from cloud_copasi.web_interface.aws import vpc_tools, task_tools, ec2_tools
from cloud_copasi.web_interface import form_tools
import tempfile, os
from cloud_copasi import settings, copasi
from cloud_copasi.copasi.model import CopasiModel
from cloud_copasi.web_interface import task_plugins
from cloud_copasi.web_interface.task_plugins import base, tools
from django.forms.forms import NON_FIELD_ERRORS
import logging

log = logging.getLogger(__name__)


class NewTaskView(RestrictedFormView):
    template_name = 'tasks/task_new.html'
    page_title = 'New task'
    
    def __init__(self, *args, **kwargs):
        self.form_class = base.BaseTaskForm
        return super(NewTaskView, self).__init__(*args, **kwargs)
    
    
    
    def get_form_kwargs(self):
        kwargs = super(NewTaskView, self).get_form_kwargs()
        kwargs['user']=self.request.user
        kwargs['task_types'] = tools.get_task_types()
        return kwargs
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        #If task_type has been set, change the form class
        task_type = request.POST.get('task_type')
        if task_type:
            task_form = tools.get_form_class(task_type)
            self.form_class = task_form
        
        
        #Ensure we have at least 1 running condor pool
        pools = CondorPool.objects.filter(user=request.user)
        if pools.count() == 0:
            request.session['errors']=[('No running compute pools', 'You must have at least 1 running compute pool before you can submit a job')]
            return HttpResponseRedirect(reverse_lazy('pool_status'))
        
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Submitting task'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Submitting a task can take several minutes'

        return super(NewTaskView,self).dispatch(request, *args, **kwargs)
    
    def form_valid(self, form,  *args, **kwargs):
        #access_key = form.cleaned_data['access_key']
        compute_pool = form.cleaned_data['compute_pool']
        assert isinstance(compute_pool, CondorPool)
        #access_key = compute_pool.vpc.access_key
        request = self.request

        #assert access_key.user == request.user
        #assert compute_pool.vpc.access_key == access_key
        
        assert compute_pool.user == request.user
        
        log.debug(compute_pool.get_pool_type())
        
        ########################################################################
        #Process the uploaded copasi file (and other files?) and create a list
        #of files to upload to s3
        ########################################################################
        
        #Handle uploaded files...
        #Ensure the directory we're adding the file to exists
        if not os.path.exists(settings.STORAGE_DIR):
            os.mkdir(settings.STORAGE_DIR)
        
        working_dir = tempfile.mkdtemp(dir=settings.STORAGE_DIR)
        model_file = request.FILES['model_file']
        
        full_filename = os.path.join(working_dir, model_file.name)

        form_tools.handle_uploaded_file(model_file, full_filename)
        
        
        task = Task()
        task.name = form.cleaned_data['name']
        task.condor_pool = form.cleaned_data['compute_pool']
        task.task_type = form.cleaned_data['task_type']
        task.original_model = full_filename

        
        
        #Get a list of all fields that are only in the task form, and not in the base

        
        extra_fields = []
        base_form = base.BaseTaskForm
        for field_name in self.form_class.base_fields:
            if field_name not in base_form.base_fields:
                extra_fields.append(field_name)
        #Save the custom task fields
        for field_name in extra_fields:
            task.set_custom_field(field_name, form.cleaned_data[field_name])
            
            
        task.save()
        
        TaskClass = tools.get_task_class(form.cleaned_data['task_type'])
        
        task_instance = TaskClass(task)
        
        #Validate the task
        valid = task_instance.validate()
        if valid != True:
            #valid message contained in valid hopefully.
            error_messages = ['Model file is not valid for the current task type',
                               str(valid),
                               ]
            form._errors[NON_FIELD_ERRORS] = forms.forms.ErrorList(error_messages)
            task.delete()
            kwargs['form'] = form
            return self.form_invalid(self, *args, **kwargs)
        
        #task_instance.initialize_subtasks()
        
        #task_instance.submit_subtask(1)
        
        return HttpResponseRedirect(reverse_lazy('my_account'))
    
class RunningTaskListView(RestrictedView):
    
    template_name = 'tasks/running_task_list.html'
    page_title = 'Running tasks'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        #Get a list of running tasks for this user
        user_tasks = Task.objects.filter(condor_pool__user=request.user)
        running_tasks = user_tasks.filter(status='new') | user_tasks.filter(status='running')
        
        kwargs['running_tasks'] =running_tasks
        
        return super(RunningTaskListView, self).dispatch(request, *args, **kwargs)

class TaskDetailsView(RestrictedView):
    
    template_name = 'tasks/task_details.html'
    page_title = 'Task status'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        task_id = kwargs.pop('task_id')
        task = Task.objects.get(id=task_id)
        assert task.condor_pool.user == request.user
        
        kwargs['task'] = task
        return super(TaskDetailsView, self).dispatch(request, *args, **kwargs)
    
class SubtaskDetailsView(RestrictedView):
    
    template_name = 'tasks/subtask_details.html'
    page_title = 'Subtask details'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        subtask_id = kwargs.pop('subtask_id')
        subtask = Subtask.objects.get(id=subtask_id)
        assert subtask.task.condor_pool.user == request.user
        
        kwargs['subtask'] = subtask
        
        kwargs['running_count'] = subtask.condorjob_set.filter(queue_status='R').count()
        kwargs['finished_count'] = subtask.condorjob_set.filter(queue_status='F').count()
        kwargs['idle_count'] = subtask.condorjob_set.filter(queue_status='I').count()
        kwargs['held_count'] = subtask.condorjob_set.filter(queue_status='H').count()
        
        
        return super(SubtaskDetailsView, self).dispatch(request, *args, **kwargs)
    
class TaskDeleteView(RestrictedView):
    
    template_name = 'tasks/task_delete.html'
    page_title = 'Delete task'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        task = Task.objects.get(id=kwargs['task_id'])
        assert task.condor_pool.user == request.user
        
        confirmed = kwargs['confirmed']
        
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Deleting Task'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Deleting a task can take several minutes'

        if not confirmed:
            kwargs['task']=task
            return super(TaskDeleteView, self).dispatch(request, *args, **kwargs)
        
        else:
            task_tools.delete_task(task)
            task.status='delete'
            task.save()
            
            return HttpResponseRedirect(reverse_lazy('running_task_list'))