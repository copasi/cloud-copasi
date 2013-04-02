from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
from django.views.generic import TemplateView, RedirectView, View, FormView
from django.views.generic.edit import FormMixin, ProcessFormView
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django import forms
from web_interface.views import RestrictedView, DefaultView, RestrictedFormView
from models import AWSAccessKey, VPC, CondorPool, CondorJob, Task
import models
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import sys
from web_interface.account.account_views import MyAccountView
from django.contrib.auth.forms import PasswordChangeForm
from boto.vpc import VPCConnection
from boto.ec2 import EC2Connection
from web_interface.aws import vpc_tools, job_tools


class NewTaskForm(forms.Form):
    name = forms.CharField()
    task_type = forms.Select(choices=models.TASK_CHOICES)
    no_of_nodes = forms.IntegerField()
    aws_access_key = forms.ChoiceField()
    
    def __init__(self, user, *args, **kwargs):
        super(NewTaskForm, self).__init__(*args, **kwargs)
        self.user = user
        access_keys = AWSAccessKey.objects.filter(user=self.user)
        self.fields['aws_access_key'].choices = ( (x, x.name) for x in access_keys)

#Generic function for saving a django UploadedFile to a destination
def handle_uploaded_file(f,destination):
    destination = open(destination, 'wb+')
    for chunk in f.chunks():
        destination.write(chunk)
    destination.close()

class NewTaskView(RestrictedFormView):
    template_name = 'jobs/job_new.html'
    page_title = 'New job'
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
        
        
        ########################################################################
        #Process the uploaded copasi file (and other files?) and create a list
        #of files to upload to s3
        ########################################################################
        
        #Handle uploaded files...
        original_model = ''
        #And process them
        #Each list contains full file paths
        model_files, data_files, condor_jobs = ([], [], []) 

        
        ########################################################################
        #Next, create the new task object and send the files over to s3
        ########################################################################
        
        task = Task()
        task.name = form.cleaned_data['name']
        task.condor_pool = CondorPool.objects.get(id=form.cleaned_data['pool'])
        task.task_type = form.cleaned_data['task_type']
        task.runs = form.cleaned_data['min_runs']
        task.max_runs = form.cleaned_data['max_runs']
        task.original_model = original_model
        task.save()
        
        
        for condor_job in condor_jobs:
            condor_job.task = task
            condor_job.save()
            
        
        #List of full file paths
        file_list = model_files + data_files
        
        key_names = job_tools.store_to_outgoing_bucket(task, file_list)
        
        
        ########################################################################
        #Notify the pool queue that a new task has been submitted
        ########################################################################
        
        #get a list of the file names of the 
        
        job_tools.notify_new_task(task, key_names)
        
        return HttpResponseRedirect(reverse_lazy('my_account_job_new'))
    
class JobNewView(RestrictedView):
    pass